import re
from typing import List, Dict, Any, Set
from loguru import logger
from app.models.api_schemas import RawApartmentInput, ModelFeatures, ApartmentFeaturesInput


class DataTransformer:
    """
    Transforms raw API input into a strictly typed ModelFeatures object compatible with the CatBoost model.
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
        try:
            features = item.features
            facts_set = {f.lower() for f in item.facts}

            # 1. Numerics & Simple calculations
            floor_val = self._get_floor_val(features.floor_number, features.total_floors_cnt)

            # 2. Parsing logic
            util_dict = self._parse_utilities(features.hcs_price)
            balcony_dict = self._parse_balcony_loggia(features.balcony_loggia_cnt)
            entrance_dict = self._get_entrance_flags(features.entrance_info, facts_set)

            # 3. Flags & Categories
            ind_proj_flg = self._get_individual_project_flag(features.construction_series)
            era_cat = self._get_era_cat(features.build_year)

            # 4. Mappings
            repair_cat = self.REPAIR_CAT_MAPPING.get(str(features.repair_cat).lower(), 0)
            parking_cat = self.PARKING_CAT_MAPPING.get(str(features.parking_cat).lower(), 0)
            heating_cat = self.HEATING_CAT_MAPPING.get(str(features.heating_cat).lower(), 0)

            # 5. OHE Groups
            house_type_flags = self._get_house_type_flags(features.house_type_cat)
            district_flags = self._get_district_flags(item.address)
            facts_flags = self._get_facts_dict(facts_set)

            # Assembly
            return ModelFeatures(
                metro_nearest_time=features.metro_nearest_time,
                total_area=features.total_area,
                floor=floor_val,
                # Facts
                **facts_flags,
                # Utilities
                utility_fixed_bill=util_dict["fixed"],
                utility_usage_bill_flg=util_dict["usage_flg"],
                utility_counters_extra_flg=util_dict["counters_flg"],
                # Financials
                deposit=features.deposit,
                comission=features.comission,
                prepayment_months_cnt=features.prepayment_months_cnt,
                rent_term_months_cnt=features.rent_term_months_cnt,
                # Rooms & Layout
                combined_bathrooms_cnt=features.combined_bathrooms_cnt,
                separate_bathrooms_cnt=features.separate_bathrooms_cnt,
                repair_cat=repair_cat,
                freight_elevators_cnt=features.freight_elevators_cnt,
                passenger_elevators_cnt=features.passenger_elevators_cnt,
                parking_cat=parking_cat,
                heating_cat=heating_cat,
                # Parsed Balconies
                balcony_cnt=balcony_dict["balcony"],
                loggia_cnt=balcony_dict["loggia"],
                # Entrance
                has_garbage_chute_flg=entrance_dict["garbage"],
                has_concierge_flg=entrance_dict["concierge"],
                entrances_cnt=features.entrances_cnt,
                # Building info
                individual_project_flg=ind_proj_flg,
                era_cat=era_cat,
                # House Type OHE
                house_type_monolithic_flg=house_type_flags["mon"],
                house_type_monolithic_brick_flg=house_type_flags["mon_brick"],
                house_type_panel_flg=house_type_flags["panel"],
                # District OHE
                district_krasnogvardeysky_flg=district_flags["krasnogv"],
                district_krasnoselsky_flg=district_flags["krasnosel"],
                district_moskovsky_flg=district_flags["mosk"],
                district_nevsky_flg=district_flags["nevsky"],
                district_other_flg=district_flags["other"],
                district_primorsky_flg=district_flags["prim"],
                district_vyborgsky_flg=district_flags["vyb"],
            )

        except Exception as e:
            logger.error(f"Error transforming item: {item.title}. Error: {e}")
            raise e

    def _get_floor_val(self, floor_number: int, total_floors: int) -> float:
        if total_floors > 0:
            return floor_number / total_floors
        return 0.0

    def _parse_utilities(self, hcs_price_str: str) -> Dict[str, int]:
        res = {"fixed": 0, "usage_flg": 0, "counters_flg": 0}
        if not hcs_price_str:
            return res

        hcs_lower = hcs_price_str.lower()
        clean_digits = re.sub(r"[^\d]", "", hcs_price_str)
        if clean_digits:
            res["fixed"] = int(clean_digits)

        res["usage_flg"] = int("не включена" in hcs_lower)
        res["counters_flg"] = int("не включена" in hcs_lower or "без счётчиков" in hcs_lower)
        return res

    def _parse_balcony_loggia(self, bl_str: str | None) -> Dict[str, int]:
        res = {"balcony": 0, "loggia": 0}
        if not bl_str:
            return res

        bl_lower = bl_str.lower()

        balcony_match = re.search(r"(\d+)\s+балк", bl_lower)
        if balcony_match:
            res["balcony"] = int(balcony_match.group(1))

        loggia_match = re.search(r"(\d+)\s+лодж", bl_lower)
        if loggia_match:
            res["loggia"] = int(loggia_match.group(1))

        return res

    def _get_entrance_flags(self, entrance_info: str | None, facts_set: Set[str]) -> Dict[str, int]:
        res = {"garbage": 0, "concierge": 0}

        if entrance_info:
            entrance_lower = entrance_info.lower()
            if "мусоропровод" in entrance_lower:
                res["garbage"] = 1
            if "консьерж" in entrance_lower:
                res["concierge"] = 1
        return res

    def _get_individual_project_flag(self, series: str | None) -> int:
        if series and "индивидуальный проект" in series.lower():
            return 1
        return 0

    def _get_era_cat(self, year: int | None) -> int:
        if not year:
            return 0
        return next((cat for cat, rule in self.ERA_RULES.items() if rule(year)), 0)

    def _get_house_type_flags(self, house_type: str | None) -> Dict[str, int]:
        ht = str(house_type).lower()
        return {
            "mon": 1 if "монолит" in ht and "кирпич" not in ht else 0,
            "mon_brick": 1 if "монолит" in ht and "кирпич" in ht else 0,
            "panel": 1 if "панель" in ht else 0,
        }

    def _get_district_flags(self, address: str) -> Dict[str, int]:
        addr = address.lower()
        flags = {
            "krasnogv": 1 if "красногвардейский" in addr else 0,
            "krasnosel": 1 if "красносельский" in addr else 0,
            "mosk": 1 if "московский" in addr else 0,
            "nevsky": 1 if "невский" in addr else 0,
            "prim": 1 if "приморский" in addr else 0,
            "vyb": 1 if "выборгский" in addr else 0,
            "other": 0,
        }

        known_sum = sum(flags.values())
        if known_sum == 0:
            # Baseline districts (Central etc) are all 0.
            # Only if it's NOT a baseline district do we mark it as "Other".
            baseline_districts = ["центральный", "петроградский", "адмиралтейский", "василеостровский"]
            if not any(d in addr for d in baseline_districts):
                flags["other"] = 1

        return flags

    def _get_facts_dict(self, facts_set: Set[str]) -> Dict[str, int]:
        return {
            "has_bath_flg": 1 if "bathtub" in facts_set else 0,
            "has_shower_flg": 1 if "shower_cabin" in facts_set else 0,
            "has_internet_flg": 1 if "internet" in facts_set else 0,
            "has_ac_flg": 1 if "ac" in facts_set else 0,
            "has_room_furniture_flg": 1 if "room_furniture" in facts_set else 0,
            "has_kitchen_furniture_flg": 1 if "kitchen_furniture" in facts_set else 0,
            "has_dishwasher_flg": 1 if "dishwasher" in facts_set else 0,
            "has_washer_flg": 1 if "washing_machine" in facts_set else 0,
            "has_tv_flg": 1 if "tv" in facts_set else 0,
            "has_fridge_flg": 1 if "refrigerator" in facts_set else 0,
        }


transformer = DataTransformer()
