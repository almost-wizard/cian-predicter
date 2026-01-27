import re
from typing import List, Optional

from bs4 import BeautifulSoup

from app.config import config
from app.core.browser import BrowserService
from app.core.logger import log
from app.core.timer import Timer
from app.models.apartment import FlatItem
from app.parser.base import BaseParser
from app.storage.writer import JsonlWriter


class CianParser(BaseParser):
    def __init__(self):
        self.browser_service = BrowserService()
        self.writer = JsonlWriter(config.OUTPUT_FILE)
        self.timer = Timer()

    async def run(self):
        await self.browser_service.start()

        try:
            # Итерация по страницам листинга
            # Диапазон от до 1000 гарантирует сбор тысяч объявлений (или продолжение с определенной страницы)
            for page_num in range(237, 1001):
                should_continue = await self.process_listing_page(page_num)

                if not should_continue:
                    log.info("No more offers found. Stopping.")

                    break

        except Exception as e:
            log.error(f"Critical error during parsing: {e}")

        finally:
            await self.browser_service.stop()

    async def process_listing_page(self, page_num: int) -> bool:
        """
        Обрабатывает страницу списка объявлений.

        Args:
            page_num (int): Номер страницы для обработки.

        Returns:
            bool: True, если объявления были найдены и следует продолжать, иначе False.
        """

        context, page = await self.browser_service.get_new_context()
        offer_urls = []

        try:
            url = f"{config.BASE_URL}?p={page_num}"

            log.info(f"Scanning listing page {page_num}: {url}")
            await page.goto(url, timeout=config.TIMEOUT, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            content = await page.content()
            offer_urls = self._extract_offer_urls(content)

        except Exception as e:
            log.error(f"Error processing listing page {page_num}: {e}")
            return True  # Продолжаем попытки со следующей страницей на случай временной ошибки

        finally:
            await context.close()

        if not offer_urls:
            log.warning(f"No offers found on page {page_num}.")
            return False

        log.info(f"Found {len(offer_urls)} offers on page {page_num}. Starting detailed parsing...")

        for offer_url in offer_urls:
            await self.process_offer_page(offer_url)

            # Случайная пауза между предложениями
            await self.timer.sleep(2, 4)

        # Случайная пауза между страницами пагинации
        await self.timer.sleep(3, 6)

        return True

    async def process_offer_page(self, url: str):
        context, page = await self.browser_service.get_new_context()
        try:
            log.debug(f"Parsing offer: {url}")
            await page.goto(url, timeout=config.TIMEOUT, wait_until="domcontentloaded")

            try:
                await page.wait_for_selector("div[data-name='AddressContainer']", timeout=5000)
            except:
                log.warning(f"Timeout waiting for page load: {url}")

            # Небольшая случайная задержка после загрузки перед "чтением"
            await self.timer.sleep(0.5, 1.5)

            content = await page.content()
            item = self._parse_detail_html(content, url)

            if item:
                self.writer.write_item(item)
                log.info(f"Saved: {item.address[:30]}... | {item.price_per_month}")
            else:
                log.warning(f"Parsed item is empty for {url}")

        except Exception as e:
            log.error(f"Failed to parse offer {url}: {e}")
        finally:
            await context.close()

    def _extract_offer_urls(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        urls = []

        # Стратегия: Пробуем несколько селекторов, замеченных на Cian
        cards = []

        # 1. Пробуем по data-name (CardComponent ИЛИ CardLayoutContainer)
        cards.extend(soup.find_all("article", {"data-name": "CardComponent"}))
        cards.extend(soup.find_all("div", {"data-name": "CardComponent"}))
        cards.extend(soup.find_all("article", {"data-name": "CardLayoutContainer"}))
        cards.extend(soup.find_all("div", {"data-name": "CardLayoutContainer"}))

        # 2. Пробуем по regex data-testid (card-item.*)
        # Это ловит <article data-testid="card-item.10">
        if not cards:
            cards.extend(soup.find_all(attrs={"data-testid": re.compile(r"^card-item")}))

        # 3. Запасной вариант: offer-card
        if not cards:
            cards.extend(soup.find_all(attrs={"data-testid": "offer-card"}))

        # Дедупликация карточек на основе адреса памяти на всякий случай
        unique_cards = list(set(cards))

        for card in unique_cards:
            link = card.find("a", href=True)
            if link:
                full_url = link["href"]
                if not full_url.startswith("http"):
                    full_url = "https://spb.cian.ru" + full_url
                urls.append(full_url)

        # Дедупликация URL
        return list(set(urls))

    def _parse_detail_html(self, html: str, url: str) -> Optional[FlatItem]:
        soup = BeautifulSoup(html, "lxml")
        item = FlatItem(url=url)

        def get_text(element):
            return element.get_text(strip=True) if element else ""

        def clean_digits(text):
            return re.sub(r"[^\d]", "", text)

        try:
            # 0. Заголовок (H1)
            h1 = soup.find("h1")
            item.title = get_text(h1)

            # 1. Адрес
            addr_container = soup.find("div", {"data-name": "AddressContainer"})
            if addr_container:
                geo_links = addr_container.find_all("a", {"data-name": "AddressItem"})
                addr_parts = [get_text(a) for a in geo_links]
                item.address = ", ".join(addr_parts)

            # 2. Метро
            metro_list = soup.find("ul", {"data-name": "UndergroundList"})
            if metro_list:
                metros = metro_list.find_all("li", {"data-name": "UndergroundItem"})
                item.metro_count = len(metros)
                if metros:
                    first_metro = metros[0]
                    time_text = get_text(first_metro)
                    match = re.search(r"(\d+\s*мин)", time_text)
                    if match:
                        item.metro_nearest_time = match.group(1)

            # 3. Цена (Основная)
            price_div = soup.find("div", {"data-testid": "price-amount"})
            if price_div:
                raw_price = get_text(price_div)
                clean = clean_digits(raw_price)
                if clean:
                    item.price_per_month = int(clean)

            # 4. Обработка фактов (Единая логика для всех блоков фактов)
            # Ищем пары ключ-значение в различных контейнерах и заполняем item.facts

            # 4.1 Факты в боковой панели
            sidebar = soup.find("div", {"data-name": "OfferFactsInSidebar"})
            if sidebar:
                fact_items = sidebar.find_all("div", {"data-name": "OfferFactItem"})
                for f in fact_items:
                    spans = f.find_all("span")
                    if len(spans) >= 2:
                        # Предположение: Первый span - ключ, последний - значение
                        key = get_text(spans[0])
                        val = get_text(spans[-1])
                        item.facts[key] = val

            # 4.2 Закрепленные фактоиды (Площадь, Этаж часто здесь)
            factoids = soup.find("div", {"data-name": "ObjectFactoids"})
            if factoids:
                items = factoids.find_all("div", {"data-name": "ObjectFactoidsItem"})
                for f in items:
                    # Часто структура: <div><span>Key</span><span>Value</span></div>
                    # Ищем текстовый контейнер внутри
                    text_container = f.find("div", class_=lambda x: x and "text" in x)
                    # Запасной вариант, если логика имени класса не сработала, просто ищем span'ы в элементе
                    if text_container:
                        spans = text_container.find_all("span")
                    else:
                        spans = f.find_all("span")

                    if len(spans) >= 2:
                        key = get_text(spans[0])
                        val = get_text(spans[1])  # Обычно второй span здесь - значение
                        item.facts[key] = val
                    elif len(spans) == 1:
                        txt = get_text(spans[0])
                        if "м²" in txt:
                            item.facts["Общая площадь"] = txt
                        if "/" in txt and any(c.isdigit() for c in txt):
                            item.facts["Этаж"] = txt

            # 4.3 Подробная сводка
            summary_container = soup.find("div", {"data-name": "OfferSummaryInfoLayout"})
            if summary_container:
                summary_items = summary_container.find_all("div", {"data-name": "OfferSummaryInfoItem"})
                for s in summary_items:
                    children = s.find_all(recursive=False)
                    if len(children) >= 2:
                        key = get_text(children[0])
                        val = get_text(children[1])
                        item.facts[key] = val

            # 5. Извлечение конкретных полей из фактов (Этаж, Площадь)
            # Итерация по собранным фактам для заполнения структурированных полей
            for key, val in item.facts.items():
                k_lower = key.lower()
                if "этаж" in k_lower and not item.floor:
                    item.floor = val
                if "площадь" in k_lower and "общая" in k_lower and not item.total_area:
                    item.total_area = val

            # Запасной вариант для Этажа/Площади из Заголовка, если все еще пусто
            if not item.floor and item.title:
                # "2-комн. кв., 55м, 3/9 этаж"
                match = re.search(r"(\d+/\d+)\s*эт", item.title)
                if match:
                    item.floor = match.group(1)

            if not item.total_area and item.title:
                match = re.search(r"(\d+[\.,]?\d*)\s*м", item.title)
                if match:
                    item.total_area = match.group(1)

            # 6. Особенности (флаги)
            features_layout = soup.find("div", {"data-name": "FeaturesLayout"})
            if features_layout:
                feature_items = features_layout.find_all("div", {"data-name": "FeaturesItem"})
                for feat in feature_items:
                    name = get_text(feat)
                    if name:
                        item.features.append(name)

        except Exception as e:
            log.error(f"Partial parsing error on {url}: {e}")

        return item
