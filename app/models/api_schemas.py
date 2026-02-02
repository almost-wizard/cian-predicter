from typing import List, Optional, Any
from pydantic import BaseModel


class ModelFeatures(BaseModel):
    """
    Строго типизированная структура признаков для ML-модели.
    Описывает вектор признаков, который ожидает CatBoost модель.
    """

    metro_nearest_time: int
    total_area: float
    floor: float
    has_bath_flg: int
    has_shower_flg: int
    has_internet_flg: int
    has_ac_flg: int
    has_room_furniture_flg: int
    has_kitchen_furniture_flg: int
    has_dishwasher_flg: int
    has_washer_flg: int
    has_tv_flg: int
    has_fridge_flg: int
    utility_fixed_bill: int
    utility_usage_bill_flg: int
    utility_counters_extra_flg: int
    comission: float
    prepayment_months_cnt: int
    rent_term_months_cnt: int
    combined_bathrooms_cnt: int
    separate_bathrooms_cnt: int
    repair_cat: int
    freight_elevators_cnt: int
    passenger_elevators_cnt: int
    parking_cat: int
    heating_cat: int
    balcony_cnt: int
    loggia_cnt: int
    has_garbage_chute_flg: int
    has_concierge_flg: int
    entrances_cnt: int
    individual_project_flg: int
    era_cat: int
    house_type_monolithic_flg: int
    house_type_monolithic_brick_flg: int
    house_type_panel_flg: int
    district_krasnogvardeysky_flg: int
    district_krasnoselsky_flg: int
    district_moskovsky_flg: int
    district_nevsky_flg: int
    district_other_flg: int
    district_primorsky_flg: int
    district_vyborgsky_flg: int

    def to_list(self) -> List[Any]:
        """
        Возвращает значения признаков в виде списка.
        Порядок значений соответствует порядку признаков модели CatBoost.
        Любое изменение порядка приведет к неверным предсказаниям.
        """
        return [
            self.metro_nearest_time,
            self.total_area,
            self.floor,
            self.has_bath_flg,
            self.has_shower_flg,
            self.has_internet_flg,
            self.has_ac_flg,
            self.has_room_furniture_flg,
            self.has_kitchen_furniture_flg,
            self.has_dishwasher_flg,
            self.has_washer_flg,
            self.has_tv_flg,
            self.has_fridge_flg,
            self.utility_fixed_bill,
            self.utility_usage_bill_flg,
            self.utility_counters_extra_flg,
            self.comission,
            self.prepayment_months_cnt,
            self.rent_term_months_cnt,
            self.combined_bathrooms_cnt,
            self.separate_bathrooms_cnt,
            self.repair_cat,
            self.freight_elevators_cnt,
            self.passenger_elevators_cnt,
            self.parking_cat,
            self.heating_cat,
            self.balcony_cnt,
            self.loggia_cnt,
            self.has_garbage_chute_flg,
            self.has_concierge_flg,
            self.entrances_cnt,
            self.individual_project_flg,
            self.era_cat,
            self.house_type_monolithic_flg,
            self.house_type_monolithic_brick_flg,
            self.house_type_panel_flg,
            self.district_krasnogvardeysky_flg,
            self.district_krasnoselsky_flg,
            self.district_moskovsky_flg,
            self.district_nevsky_flg,
            self.district_other_flg,
            self.district_primorsky_flg,
            self.district_vyborgsky_flg,
        ]


class ApartmentFeaturesInput(BaseModel):
    """
    Вложенный объект 'features' из входящего JSON.
    Содержит структурированные характеристики квартиры.
    """

    hcs_price: str = "0"
    comission: float = 0.0
    metro_cnt: int = 0
    metro_nearest_time: int = 0
    prepayment_months_cnt: int = 0
    rent_term_months_cnt: int = 0
    total_area: float
    living_area: Optional[float] = 0
    kitchen_area: Optional[float] = 0
    floor_number: int
    total_floors_cnt: int = 0
    layout_cat: Optional[str] = ""
    repair_cat: Optional[str] = "Без ремонта"
    heating_cat: Optional[str] = "Нет информации"
    house_type_cat: Optional[str] = ""
    parking_cat: Optional[str] = ""
    balcony_loggia_cnt: Optional[str] = ""
    entrance_info: Optional[str] = ""
    construction_series: Optional[str] = ""
    combined_bathrooms_cnt: int = 0
    separate_bathrooms_cnt: int = 0
    passenger_elevators_cnt: int = 0
    freight_elevators_cnt: int = 0
    entrances_cnt: int = 0
    build_year: Optional[int] = None


class RawApartmentInput(BaseModel):
    """
    Входной формат данных для API.
    Соответствует JSON-структуре, приходящей от клиента.
    """

    title: str = ""
    price_per_month: Optional[int] = None
    address: str
    features: ApartmentFeaturesInput
    facts: List[str] = []


class PredictionResponseItem(BaseModel):
    """
    Объект результата предсказания для одной квартиры.
    """

    predicted_price: int
    price_range_low: int
    price_range_high: int
    undervalued_percent: Optional[float] = None


class PredictionResponse(BaseModel):
    """
    Главный объект ответа API.
    """

    predictions: List[PredictionResponseItem]
