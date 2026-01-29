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

        # Состояние парсера
        self.current_page_timeout = config.TIMEOUT  # Таймаут для page.goto
        self.current_retry_delay = config.BASE_RETRY_DELAY  # Пауза перед ретраем
        self.consecutive_successes = 0

    async def _retry_action(self, action_name: str, action_func):
        """
        Универсальная обертка для выполнения действий с ретраями и раздельным управлением таймаутами.
        """
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                # Выполняем функцию
                await action_func()

                # Если успешно:
                self.consecutive_successes += 1
                if self.consecutive_successes >= config.SUCCESS_THRESHOLD_FOR_RESET:
                    # Сброс параметров к дефолтным при стабильной работе
                    if self.current_page_timeout > config.TIMEOUT or self.current_retry_delay > config.BASE_RETRY_DELAY:
                        log.info("Stable connection detected. Resetting timeouts/delays to defaults.")
                        self.current_page_timeout = config.TIMEOUT
                        self.current_retry_delay = config.BASE_RETRY_DELAY

                    self.consecutive_successes = 0
                return True

            except Exception as e:
                err_msg = str(e).lower()
                is_bot_block = "anti-bot" in err_msg or "vpn" in err_msg or "captcha" in err_msg

                log.warning(f"Error during '{action_name}' (Attempt {attempt}/{config.MAX_RETRIES}): {e}")

                if is_bot_block:
                    # При бане (VPN/Капча) главное - подождать подольше
                    new_delay = int(self.current_retry_delay * config.RETRY_DELAY_MULTIPLIER)
                    self.current_retry_delay = min(new_delay, config.MAX_RETRY_DELAY)
                    log.warning(f"Bot block detected! Increasing retry delay to {self.current_retry_delay}s")
                else:
                    # При сетевых ошибках немного увеличиваем таймаут загрузки и паузу
                    new_timeout = int(self.current_page_timeout * 1.5)
                    self.current_page_timeout = min(new_timeout, config.MAX_PAGE_TIMEOUT)

                    new_delay = int(self.current_retry_delay * 1.5)
                    self.current_retry_delay = min(new_delay, 60)  # Для сети не ждем так долго, как для бана

                    log.info(f"Network glitch. Increasing page timeout to {self.current_page_timeout}ms")

                # Сбрасываем счетчик успехов
                self.consecutive_successes = 0

                # Пауза перед следующей попыткой
                log.info(f"Waiting {self.current_retry_delay}s before retry...")
                await self.timer.sleep(self.current_retry_delay, self.current_retry_delay)

        log.error(f"Failed '{action_name}' after {config.MAX_RETRIES} attempts.")
        return False

    async def run(self):
        await self.browser_service.start()

        # Создаем постоянный контекст для навигации по каталогу
        listing_context, listing_page = await self.browser_service.get_new_context()

        try:
            log.info(f"Opening Catalog: {config.BASE_URL}")

            # Переходим на стартовую страницу
            await listing_page.goto(config.BASE_URL, timeout=config.TIMEOUT, wait_until="domcontentloaded")
            await self.timer.sleep(2, 4)  # Даем время на полную прогрузку

            # Инициализируем номер страницы. По умолчанию 1.
            page_num = 1

            # Логика "умного" пропуска страниц
            if config.START_PAGE > 1:
                page_num = await self._fast_forward_to_page(listing_page, config.START_PAGE)

            while True:
                log.info(f"Processing listing page {page_num}...")

                # 1. Извлекаем URL предложений с текущего вида страницы
                content = await listing_page.content()
                offer_urls = self._extract_offer_urls(content)
                log.info(f"Found {len(offer_urls)} offers on page {page_num}.")

                # 2. Обрабатываем каждое предложение (в отдельных контекстах)
                if offer_urls:
                    for offer_url in offer_urls:
                        await self.process_offer_page(offer_url)
                        # Короткая пауза между открытиями карточек
                        await self.timer.sleep(1, 3)
                else:
                    log.warning(f"No offers found on page {page_num}. Might be captcha or empty page.")

                # 3. Переход на следующую страницу
                if not await self._click_next_page(listing_page):
                    log.info("Pagination ended or failed.")
                    break

                page_num += 1
                # Страховочный лимит (на всякий случай)
                if page_num > 1000:
                    log.info("Reached page limit (1000). Stopping.")
                    break

        except Exception as e:
            log.error(f"Critical error during parsing: {e}")
        finally:
            await listing_context.close()
            await self.browser_service.stop()

    async def _fast_forward_to_page(self, page, target_page: int) -> int:
        """
        Быстро перематывает пагинацию к целевой странице.
        """
        log.info(f"Fast-forwarding to page {target_page}...")

        while True:
            # Обновляем текущее состояние (без ретраев, это чтение)
            nav = page.locator('nav[data-name="Pagination"]')
            current_span = nav.locator("button[disabled] span")

            current_val = 1
            if await current_span.count() > 0:
                txt = await current_span.first.text_content()
                if txt and txt.strip().isdigit():
                    current_val = int(txt.strip())

            log.info(f"Current page on site: {current_val}")
            if current_val >= target_page:
                log.info(f"Reached or passed target page {target_page}.")
                return current_val

            # Ищем кнопку для прыжка
            spans = nav.locator("span")
            count = await spans.count()
            best_jump_span_idx = -1
            best_jump_val = -1

            for i in range(count):
                txt = await spans.nth(i).text_content()
                if not txt:
                    continue
                txt = txt.strip()
                if txt.isdigit():
                    val = int(txt)
                    if val == target_page:
                        best_jump_span_idx = i
                        best_jump_val = val
                        break
                    if val > current_val and val > best_jump_val:
                        best_jump_span_idx = i
                        best_jump_val = val

            if best_jump_span_idx != -1:
                log.info(f"Jumping from {current_val} to {best_jump_val}...")

                # Функция клика прыжка для ретрая
                async def _jump_task():
                    target_span = spans.nth(best_jump_span_idx)
                    btn = target_span.locator("..")
                    await btn.scroll_into_view_if_needed()
                    await btn.click(timeout=self.current_page_timeout)
                    await page.wait_for_load_state("domcontentloaded", timeout=self.current_page_timeout)
                    await self.timer.sleep(2, 4)

                success = await self._retry_action(f"jump_to_{best_jump_val}", _jump_task)
                if not success:
                    log.error("Jump failed even after retries.")
                    if not await self._click_next_page(page):
                        return current_val
            else:
                log.info("No numeric jump found, clicking 'Next'...")
                if not await self._click_next_page(page):
                    return current_val

    async def _click_next_page(self, page) -> bool:
        """Клик по кнопке 'Дальше' с ретраями."""

        async def _click_task():
            pagination_nav = page.locator('nav[data-name="Pagination"]')
            next_span = pagination_nav.locator("span", has_text="Дальше")

            if await next_span.count() == 0:
                all_buttons = pagination_nav.locator("button")
                if await all_buttons.count() > 0:
                    next_button = all_buttons.nth(await all_buttons.count() - 1)
                else:
                    raise Exception("No buttons in pagination nav")
            else:
                next_button = next_span.locator("..")

            if await next_button.count() == 0 or await next_button.is_disabled():
                raise Exception("Next button not found or disabled")

            await next_button.scroll_into_view_if_needed()
            await next_button.click(timeout=self.current_page_timeout)

            # Ждем загрузки
            await page.wait_for_load_state("domcontentloaded", timeout=self.current_page_timeout)
            await self.timer.sleep(3, 5)

        return await self._retry_action("click_next_page", _click_task)

    async def process_offer_page(self, url: str):
        # Обертка для логики одного объявления
        async def _parse_task():
            context, page = await self.browser_service.get_new_context()
            try:
                log.debug(f"Parsing offer: {url} (Timeout: {self.current_page_timeout}ms)")
                await page.goto(url, timeout=self.current_page_timeout, wait_until="domcontentloaded")

                try:
                    await page.wait_for_selector("div[data-name='AddressContainer']", timeout=5000)
                except:
                    pass

                await self.timer.sleep(0.5, 1.5)
                content = await page.content()
                item = self._parse_detail_html(content, url)

                if item:
                    self.writer.write_item(item)
                    log.info(f"Saved: {item.address[:30]}... | {item.price_per_month}")
                else:
                    log.warning(f"Parsed item is empty for {url}")
            finally:
                await context.close()

        # Запускаем через ретрай-механизм
        await self._retry_action(f"parse_offer_{url}", _parse_task)

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

        # 0. Заголовок (H1) и проверка на блокировку
        h1 = soup.find("h1")
        title_text = get_text(h1)

        # Список стоп-слов, указывающих на бан
        block_keywords = ["vpn", "доступ ограничен", "captcha", "капча", "security check"]
        if any(w in title_text.lower() for w in block_keywords):
            raise Exception(f"Anti-Bot Block detected: {title_text}")

        item.title = title_text

        try:
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

            # Если цена не найдена - это критично для нашего датасета
            if item.price_per_month is None:
                # Возможно, верстка отличается или это архивное объявление
                # Проверим на "снято с публикации"
                if "снято" in html.lower() or "архив" in html.lower():
                    log.warning(f"Offer {url} seems to be archived/inactive.")
                    return None  # Не ретраим, просто пропускаем

                # Иначе считаем это ошибкой парсинга и пробуем ретрай (вдруг не прогрузилось)
                raise Exception("Price not found on page")

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
            # Если это наше исключение про бан - пробрасываем выше
            if "Anti-Bot" in str(e) or "Price not found" in str(e):
                raise e
            log.error(f"Partial parsing error on {url}: {e}")

        return item
