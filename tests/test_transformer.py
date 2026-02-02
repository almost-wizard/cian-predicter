import pytest
from app.services.transformer_service import TransformerService
from app.models.api_schemas import RawApartmentInput, ApartmentFeaturesInput


class TestTransformerService:
    @pytest.fixture
    def t(self):
        return TransformerService()

    # --- Unit Tests for Helper Methods ---
    def test_get_floor_val(self, t):
        assert t._get_floor_val(5, 10) == 0.5
        assert t._get_floor_val(5, 0) == 0.0
        assert t._get_floor_val(0, 5) == 0.0

    def test_parse_utilities(self, t):
        # Case 1: Fixed price, included
        res = t._parse_utilities("10 000 ₽ (счётчики включены)")
        assert res["utility_fixed_bill"] == 10000
        assert res["utility_usage_bill_flg"] == 0
        assert res["utility_counters_extra_flg"] == 0

        # Case 2: Not included
        res = t._parse_utilities("5000 ₽ (ку не включена)")
        assert res["utility_fixed_bill"] == 5000
        assert res["utility_usage_bill_flg"] == 1
        assert res["utility_counters_extra_flg"] == 1

        # Case 3: Empty
        res = t._parse_utilities("")
        assert res["utility_fixed_bill"] == 0

        # Case 4: Text without digits
        res = t._parse_utilities("Включено")
        assert res["utility_fixed_bill"] == 0

    def test_parse_balcony_loggia(self, t):
        assert t._parse_balcony_loggia("1 балк") == {"balcony_cnt": 1, "loggia_cnt": 0}
        assert t._parse_balcony_loggia("2 лодж") == {"balcony_cnt": 0, "loggia_cnt": 2}
        assert t._parse_balcony_loggia("1 балк, 1 лодж") == {"balcony_cnt": 1, "loggia_cnt": 1}
        assert t._parse_balcony_loggia(None) == {"balcony_cnt": 0, "loggia_cnt": 0}
        assert t._parse_balcony_loggia("") == {"balcony_cnt": 0, "loggia_cnt": 0}

    def test_get_entrance_flags(self, t):
        # Case 1: Entrance info present
        res = t._get_entrance_flags("Есть мусоропровод", set())
        assert res["has_garbage_chute_flg"] == 1
        assert res["has_concierge_flg"] == 0

        res = t._get_entrance_flags("Есть консьерж", set())
        assert res["has_garbage_chute_flg"] == 0
        assert res["has_concierge_flg"] == 1

        res = t._get_entrance_flags("мусоропровод, консьерж", set())
        assert res["has_garbage_chute_flg"] == 1
        assert res["has_concierge_flg"] == 1

        # Case 2: Entrance info missing -> Flags are 0
        res = t._get_entrance_flags(None, {"мусоропровод"})
        assert res["has_garbage_chute_flg"] == 0

        res = t._get_entrance_flags("", {"консьерж"})
        assert res["has_concierge_flg"] == 0

    def test_get_individual_project_flag(self, t):
        assert t._get_individual_project_flag("Индивидуальный проект") == 1
        assert t._get_individual_project_flag("137 серия") == 0
        assert t._get_individual_project_flag(None) == 0

    def test_get_era_cat(self, t):
        assert t._get_era_cat(1900) == 1
        assert t._get_era_cat(1917) == 1
        assert t._get_era_cat(1950) == 2
        assert t._get_era_cat(1991) == 2
        assert t._get_era_cat(2000) == 3
        assert t._get_era_cat(2013) == 3
        assert t._get_era_cat(2020) == 4
        assert t._get_era_cat(None) == 0

    def test_get_house_type_flags(self, t):
        # Monolith
        res = t._get_house_type_flags("Монолитный")
        assert res["house_type_monolithic_flg"] == 1
        assert res["house_type_monolithic_brick_flg"] == 0
        assert res["house_type_panel_flg"] == 0

        # Panel
        res = t._get_house_type_flags("Панельный")
        assert res["house_type_monolithic_flg"] == 0
        assert res["house_type_panel_flg"] == 1

        # Monolith-Brick
        res = t._get_house_type_flags("Монолитно-кирпичный")
        assert res["house_type_monolithic_flg"] == 0
        assert res["house_type_monolithic_brick_flg"] == 1

    def test_get_district_flags(self, t):
        # Specific district
        res = t._get_district_flags("Санкт-Петербург, р-н Московский, ул. Типанова")
        assert res["district_moskovsky_flg"] == 1
        assert res["district_other_flg"] == 0

        # Baseline district (Central) -> All 0
        res = t._get_district_flags("Санкт-Петербург, р-н Центральный, Невский пр.")
        assert res["district_moskovsky_flg"] == 0
        assert res["district_other_flg"] == 0  # Correct, Central is baseline

        # Unknown district -> Other
        res = t._get_district_flags("Санкт-Петербург, р-н Колпинский")
        assert res["district_other_flg"] == 1

    # --- Integration Test ---

    def test_transform_full(self, t):
        raw = RawApartmentInput(
            title="Test apt",
            address="Санкт-Петербург, р-н Московский",
            features=ApartmentFeaturesInput(
                total_area=50.0,
                metro_nearest_time=10,
                floor_number=5,
                total_floors_cnt=10,
                hcs_price="5000",
                balcony_loggia_cnt="1 балк",
                build_year=2020,
                house_type_cat="Монолитный",
                construction_series="Индивидуальный проект",
            ),
            facts=["internet", "bathtub"],
        )

        model_features = t.transform(raw)

        assert model_features.total_area == 50.0
        assert model_features.floor == 0.5
        assert model_features.balcony_cnt == 1
        assert model_features.era_cat == 4
        assert model_features.house_type_monolithic_flg == 1
        assert model_features.individual_project_flg == 1
        assert model_features.district_moskovsky_flg == 1
        assert model_features.has_internet_flg == 1
