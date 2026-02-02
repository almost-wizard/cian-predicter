import re
from typing import Dict, Set
from loguru import logger
from app.models.api_schemas import RawApartmentInput, ModelFeatures


class TransformerService:
    """
    Сервис трансформации данных.
    Преобразует входные данные API в вектор признаков модели.
    """

    REPAIR_CAT_MAPPING = {
        "без ремонта": 0,
        "косметический": 1,
        "евроремонт": 2,
        "дизайнерский": 3,
    }

    PARKING_CAT_MAPPING = {
        "наземная": 1,
        "открытая": 1,
        "многоуровневая": 2,
        "подземная": 2,
    }

    HEATING_CAT_MAPPING = {
        "нет информации": 0,
        "печь": 1,
        "центральное": 1,
        "автономная котельная": 2,
        "индивидуальный тепловой пункт": 3,
        "котел/квартирное отопление": 3,
    }

    ERA_RULES = {
        1: lambda y: y <= 1917,
        2: lambda y: 1917 < y <= 1991,
        3: lambda y: 1991 < y <= 2013,
        4: lambda y: y > 2013,
    }

    def transform(self, item: RawApartmentInput) -> ModelFeatures:
        """
        Основной метод преобразования объекта квартиры в признаки для модели.
        """
        try:
            features = item.features
            facts_set = {f.lower() for f in item.facts}

            # 1. Числовые признаки и простые вычисления
            metro_nearest_time = features.metro_nearest_time
            total_area = features.total_area
            floor_val = self._get_floor_val(features.floor_number, features.total_floors_cnt)

            # 2. Логика парсинга текста
            util_dict = self._parse_utilities(features.hcs_price)
            balcony_dict = self._parse_balcony_loggia(features.balcony_loggia_cnt)
            entrance_dict = self._get_entrance_flags(features.entrance_info, facts_set)

            # 3. Флаги и категории
            ind_proj_flg = self._get_individual_project_flag(features.construction_series)
            era_cat = self._get_era_cat(features.build_year)

            # 4. Маппинг категориальных значений
            repair_cat = self.REPAIR_CAT_MAPPING.get(str(features.repair_cat).lower(), 0)
            parking_cat = self.PARKING_CAT_MAPPING.get(str(features.parking_cat).lower(), 0)
            heating_cat = self.HEATING_CAT_MAPPING.get(str(features.heating_cat).lower(), 0)

            # 5. One-Hot Encoding групп признаков
            house_type_flags = self._get_house_type_flags(features.house_type_cat)
            district_flags = self._get_district_flags(item.address)
            facts_flags = self._get_facts_dict(facts_set)

            # Сборка финального объекта с использованием **kwargs распаковки
            return ModelFeatures(
                metro_nearest_time=metro_nearest_time,
                total_area=total_area,
                floor=floor_val,
                # Факты (удобства)
                **facts_flags,
                # Коммунальные платежи
                **util_dict,
                # Финансовые показатели
                comission=features.comission,
                prepayment_months_cnt=features.prepayment_months_cnt,
                rent_term_months_cnt=features.rent_term_months_cnt,
                # Комнаты и планировка
                combined_bathrooms_cnt=features.combined_bathrooms_cnt,
                separate_bathrooms_cnt=features.separate_bathrooms_cnt,
                repair_cat=repair_cat,
                freight_elevators_cnt=features.freight_elevators_cnt,
                passenger_elevators_cnt=features.passenger_elevators_cnt,
                parking_cat=parking_cat,
                heating_cat=heating_cat,
                # Балконы / лоджии
                **balcony_dict,
                # Подъезд
                **entrance_dict,
                entrances_cnt=features.entrances_cnt,
                # Информация о здании
                individual_project_flg=ind_proj_flg,
                era_cat=era_cat,
                # Тип дома (OHE)
                **house_type_flags,
                # Районы (OHE)
                **district_flags,
            )

        except Exception as e:
            logger.error(f"Ошибка при трансформации объекта: {item.title}. Ошибка: {e}")
            raise e

    def _get_floor_val(self, floor_number: int, total_floors: int) -> float:
        """Вычисляет относительный этаж (0.0 - 1.0)."""
        if total_floors > 0:
            return floor_number / total_floors
        return 0.0

    def _parse_utilities(self, hcs_price_str: str) -> Dict[str, int]:
        """Парсит строку коммунальных платежей."""
        res = {"utility_fixed_bill": 0, "utility_usage_bill_flg": 0, "utility_counters_extra_flg": 0}
        if not hcs_price_str:
            return res

        hcs_lower = hcs_price_str.lower()
        clean_digits = re.sub(r"[^\d]", "", hcs_price_str)
        if clean_digits:
            res["utility_fixed_bill"] = int(clean_digits)

        res["utility_usage_bill_flg"] = int("не включена" in hcs_lower)
        res["utility_counters_extra_flg"] = int("не включена" in hcs_lower or "без счётчиков" in hcs_lower)
        return res

    def _parse_balcony_loggia(self, bl_str: str | None) -> Dict[str, int]:
        """Извлекает количество балконов и лоджий из строки."""
        res = {"balcony_cnt": 0, "loggia_cnt": 0}
        if not bl_str:
            return res

        bl_lower = bl_str.lower()

        balcony_match = re.search(r"(\d+)\s+балк", bl_lower)
        if balcony_match:
            res["balcony_cnt"] = int(balcony_match.group(1))

        loggia_match = re.search(r"(\d+)\s+лодж", bl_lower)
        if loggia_match:
            res["loggia_cnt"] = int(loggia_match.group(1))

        return res

    def _get_entrance_flags(self, entrance_info: str | None, facts_set: Set[str]) -> Dict[str, int]:
        """Определяет наличие мусоропровода и консьержа."""
        res = {"has_garbage_chute_flg": 0, "has_concierge_flg": 0}

        if entrance_info:
            entrance_lower = entrance_info.lower()
            if "мусоропровод" in entrance_lower:
                res["has_garbage_chute_flg"] = 1
            if "консьерж" in entrance_lower:
                res["has_concierge_flg"] = 1
        return res

    def _get_individual_project_flag(self, series: str | None) -> int:
        """Проверяет, является ли проект индивидуальным."""
        if series and "индивидуальный проект" in series.lower():
            return 1
        return 0

    def _get_era_cat(self, year: int | None) -> int:
        """Определяет категорию эпохи постройки."""
        if not year:
            return 0
        return next((cat for cat, rule in self.ERA_RULES.items() if rule(year)), 0)

    def _get_house_type_flags(self, house_type: str | None) -> Dict[str, int]:
        """Формирует OHE флаги для типа дома."""
        ht = str(house_type).lower()
        return {
            "house_type_monolithic_flg": 1 if "монолит" in ht and "кирпич" not in ht else 0,
            "house_type_monolithic_brick_flg": 1 if "монолит" in ht and "кирпич" in ht else 0,
            "house_type_panel_flg": 1 if "панель" in ht else 0,
        }

    def _get_district_flags(self, address: str) -> Dict[str, int]:
        """Формирует OHE флаги для районов Санкт-Петербурга."""
        addr = address.lower()
        flags = {
            "district_krasnogvardeysky_flg": 1 if "красногвардейский" in addr else 0,
            "district_krasnoselsky_flg": 1 if "красносельский" in addr else 0,
            "district_moskovsky_flg": 1 if "московский" in addr else 0,
            "district_nevsky_flg": 1 if "невский" in addr else 0,
            "district_primorsky_flg": 1 if "приморский" in addr else 0,
            "district_vyborgsky_flg": 1 if "выборгский" in addr else 0,
        }

        # Логика для "Другого" района
        flags["district_other_flg"] = int(sum(flags.values()) == 0)

        return flags

    def _get_facts_dict(self, facts_set: Set[str]) -> Dict[str, int]:
        """
        Формирует словарь флагов удобств на основе списка фактов.
        Поддерживает поиск как английских (internal keys), так и русских названий.
        """
        return {
            "has_bath_flg": 1 if "bathtub" in facts_set or "ванна" in facts_set else 0,
            "has_shower_flg": 1 if "shower_cabin" in facts_set or "душевая кабина" in facts_set else 0,
            "has_internet_flg": 1 if "internet" in facts_set or "интернет" in facts_set else 0,
            "has_ac_flg": 1 if "ac" in facts_set or "кондиционер" in facts_set else 0,
            "has_room_furniture_flg": 1 if "room_furniture" in facts_set or "мебель в комнатах" in facts_set else 0,
            "has_kitchen_furniture_flg": 1 if "kitchen_furniture" in facts_set or "мебель на кухне" in facts_set else 0,
            "has_dishwasher_flg": 1 if "dishwasher" in facts_set or "посудомоечная машина" in facts_set else 0,
            "has_washer_flg": 1 if "washing_machine" in facts_set or "стиральная машина" in facts_set else 0,
            "has_tv_flg": 1 if "tv" in facts_set or "телевизор" in facts_set else 0,
            "has_fridge_flg": 1 if "refrigerator" in facts_set or "холодильник" in facts_set else 0,
        }
