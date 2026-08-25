from src.extraction.requirement_extractor import RequirementExtractor


def test_mandatory_and_confidence():
    extractor = RequirementExtractor()

    tests = [
        ("Python obrigatório.", "python", True, 0.95),
        (
            "Experiência com Docker será um diferencial.",
            "docker",
            False,
            0.90,
        ),
        ("Conhecimento em React.", "react", False, 0.80),
    ]

    for text, expected_name, expected_mandatory, expected_confidence in tests:
        requirements = extractor.extract("test", text)

        assert len(requirements) == 1

        requirement = requirements[0]

        assert requirement.name == expected_name
        assert requirement.mandatory == expected_mandatory
        assert requirement.extraction_confidence == expected_confidence