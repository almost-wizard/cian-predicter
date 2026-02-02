from typing import List, Optional, Any
from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    """
    Вклад отдельного признака в предсказание цены.
    """

    feature_name: str = Field(..., examples=["total_area"], description="Название признака")
    influence: float = Field(..., examples=[0.05], description="Величина влияния признака на предсказание")


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

    @classmethod
    def get_feature_names(cls) -> List[str]:
        return [
            "metro_nearest_time",
            "total_area",
            "floor",
            "has_bath_flg",
            "has_shower_flg",
            "has_internet_flg",
            "has_ac_flg",
            "has_room_furniture_flg",
            "has_kitchen_furniture_flg",
            "has_dishwasher_flg",
            "has_washer_flg",
            "has_tv_flg",
            "has_fridge_flg",
            "utility_fixed_bill",
            "utility_usage_bill_flg",
            "utility_counters_extra_flg",
            "comission",
            "prepayment_months_cnt",
            "rent_term_months_cnt",
            "combined_bathrooms_cnt",
            "separate_bathrooms_cnt",
            "repair_cat",
            "freight_elevators_cnt",
            "passenger_elevators_cnt",
            "parking_cat",
            "heating_cat",
            "balcony_cnt",
            "loggia_cnt",
            "has_garbage_chute_flg",
            "has_concierge_flg",
            "entrances_cnt",
            "individual_project_flg",
            "era_cat",
            "house_type_monolithic_flg",
            "house_type_monolithic_brick_flg",
            "house_type_panel_flg",
            "district_krasnogvardeysky_flg",
            "district_krasnoselsky_flg",
            "district_moskovsky_flg",
            "district_nevsky_flg",
            "district_other_flg",
            "district_primorsky_flg",
            "district_vyborgsky_flg",
        ]

    def to_list(self) -> List[Any]:
        return [getattr(self, name) for name in self.get_feature_names()]


class ApartmentFeaturesInput(BaseModel):
    """
    Вложенный объект 'features' из входящего JSON.
    Содержит структурированные характеристики квартиры.
    """

    hcs_price: str = Field("0", examples=["5000 ₽ (счётчики включены)"], description="Стоимость аренды")
    comission: float = Field(0.0, examples=[0.5], description="Комиссия (0.5 = 50%)")
    metro_cnt: int = Field(0, examples=[2], description="Количество станций метро рядом")
    metro_nearest_time: int = Field(0, examples=[10], description="Время до метро пешком (мин)")
    prepayment_months_cnt: int = Field(0, examples=[3], description="Предоплата (мес)")
    rent_term_months_cnt: int = Field(11, examples=[11], description="Срок аренды (мес)")
    total_area: float = Field(..., examples=[52.5], description="Общая площадь (м²)")
    living_area: Optional[float] = Field(0, examples=[30.0], description="Жилая площадь (м²)")
    kitchen_area: Optional[float] = Field(0, examples=[10.0], description="Площадь кухни (м²)")
    floor_number: int = Field(..., examples=[5], description="Этаж")
    total_floors_cnt: int = Field(0, examples=[10], description="Всего этажей в доме")
    layout_cat: Optional[str] = Field("", examples=["Смежная"], description="Тип планировки")
    repair_cat: Optional[str] = Field("Без ремонта", examples=["Евроремонт"], description="Тип ремонта")
    heating_cat: Optional[str] = Field("Нет информации", examples=["Центральное"], description="Тип отопления")
    house_type_cat: Optional[str] = Field("", examples=["Монолитный"], description="Тип дома")
    parking_cat: Optional[str] = Field("", examples=["Наземная"], description="Тип парковки")
    balcony_loggia_cnt: Optional[str] = Field(
        "", examples=["1 балкон / 2 лоджии"], description="Строка с кол-вом балконов/лоджий"
    )
    entrance_info: Optional[str] = Field("", examples=["Консьерж, мусоропровод"], description="Информация о подъезде")
    construction_series: Optional[str] = Field("", examples=["Индивидуальный проект"], description="Строительная серия")
    combined_bathrooms_cnt: int = Field(0, examples=[1], description="Кол-во совмещенных санузлов")
    separate_bathrooms_cnt: int = Field(0, examples=[1], description="Кол-во раздельных санузлов")
    passenger_elevators_cnt: int = Field(0, examples=[1], description="Кол-во пассажирских лифтов")
    freight_elevators_cnt: int = Field(0, examples=[0], description="Кол-во грузовых лифтов")
    entrances_cnt: int = Field(0, examples=[1], description="Кол-во подъездов")
    build_year: Optional[int] = Field(None, examples=[2010], description="Год постройки")


class RawApartmentInput(BaseModel):
    """
    Входной формат данных для API.
    """

    title: str = Field("", examples=["Сдаются 2-комн. апартаменты"], description="Заголовок объявления")
    price_per_month: Optional[int] = Field(None, examples=[45000], description="Текущая цена (для оценки)")
    address: str = Field(
        ...,
        examples=["Санкт-Петербург, р-н Московский, Гагаринское, Витебский просп., 99к1"],
        description="Полный адрес",
    )
    features: ApartmentFeaturesInput
    facts: List[str] = Field(
        [],
        examples=[
            [
                "shower_cabin",
                "internet",
                "tv",
                "room_furniture",
                "kitchen_furniture",
                "dishwasher",
                "washing_machine",
                "tv",
                "refrigerator",
            ]
        ],
        description="Список удобств (английские теги)",
    )


class PredictionResponseItem(BaseModel):
    """
    Объект результата предсказания для одной квартиры.
    """

    predicted_price: int = Field(..., examples=[62000], description="Предсказанная цена")
    price_range_low: int = Field(..., examples=[52700], description="Нижняя граница")
    price_range_high: int = Field(..., examples=[71300], description="Верхняя граница")
    undervalued_percent: Optional[float] = Field(None, examples=[11.3], description="процент недооцененности")
    feature_contributions: List[FeatureContribution] = Field(
        [],
        examples=[
            [
                {"feature_name": "total_area", "influence": 0.13},
                {"feature_name": "district_moskovsky_flg", "influence": -0.04},
            ]
        ],
        description="Вклад признаков (SHAP values)",
    )


class PredictionResponse(BaseModel):
    """
    Главный объект ответа API.
    """

    predictions: List[PredictionResponseItem]
