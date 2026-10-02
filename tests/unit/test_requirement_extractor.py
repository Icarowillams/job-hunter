from src.extraction.requirement_extractor import RequirementExtractor


def test_mandatory_and_confidence():
    extractor = RequirementExtractor()

    tests = [
        ("Python obrigat\u00f3rio.", "python", True, 0.95),
        (
            "Experi\u00eancia com Docker ser\u00e1 um diferencial.",
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


def test_mandatory_contextual_phrases():
    extractor = RequirementExtractor()

    tests = [
        ("Java is necessary.", "java"),
        ("Java is mandatory.", "java"),
        ("Java is required.", "java"),
        ("Java must have.", "java"),
    ]

    for text, expected_name in tests:
        requirements = extractor.extract("test", text)

        assert len(requirements) == 1

        requirement = requirements[0]

        assert requirement.name == expected_name
        assert requirement.mandatory is True
        assert requirement.extraction_confidence == 0.95


def test_optional_contextual_phrases_remain_optional():
    extractor = RequirementExtractor()

    tests = [
        ("Java is a plus.", "java"),
        ("Java is preferred.", "java"),
        ("Java is nice to have.", "java"),
    ]

    for text, expected_name in tests:
        requirements = extractor.extract("test", text)

        assert len(requirements) == 1

        requirement = requirements[0]

        assert requirement.name == expected_name
        assert requirement.mandatory is False
        assert requirement.extraction_confidence == 0.90


def test_skills_in_mandatory_requirements_section_are_mandatory():
    requirements = RequirementExtractor().extract(
        "test",
        "Requisitos obrigatórios:\nPython\nDocker",
    )

    assert {item.name for item in requirements} == {"python", "docker"}
    assert all(item.mandatory is True for item in requirements)


def test_requirement_prose_starting_with_knowledge_does_not_end_section():
    requirements = RequirementExtractor().extract(
        "test",
        "Requisitos obrigatórios:\n"
        "Conhecimentos sólidos em Java 17 ou superior;\n"
        "Experiência com Spring Boot;",
    )

    by_name = {item.name: item for item in requirements}
    assert by_name["java"].mandatory is True
    assert by_name["spring"].mandatory is True


def test_isolated_knowledge_heading_ends_mandatory_section():
    requirements = RequirementExtractor().extract(
        "test",
        "Requisitos obrigatórios:\nJava\nConhecimentos\nDocker",
    )

    by_name = {item.name: item for item in requirements}
    assert by_name["java"].mandatory is True
    assert by_name["docker"].mandatory is False


def test_generic_requirements_section_does_not_make_skills_mandatory():
    requirements = RequirementExtractor().extract(
        "test",
        "Requisitos:\nPython\nDocker",
    )

    assert {item.name for item in requirements} == {"python", "docker"}
    assert all(item.mandatory is False for item in requirements)


def test_new_section_ends_mandatory_requirements_context():
    requirements = RequirementExtractor().extract(
        "test",
        "Requisitos obrigatórios:\nPython\nDiferenciais:\nDocker",
    )

    by_name = {item.name: item for item in requirements}
    assert by_name["python"].mandatory is True
    assert by_name["docker"].mandatory is False


def test_optional_language_overrides_mandatory_section():
    cases = (
        ("diferencial", "Docker será um diferencial"),
        ("preferred", "React is preferred"),
        ("nice to have", "Java is nice to have"),
    )

    for _, optional_clause in cases:
        requirements = RequirementExtractor().extract(
            "test",
            f"Requisitos obrigatórios:\n{optional_clause}",
        )

        assert len(requirements) == 1
        assert requirements[0].mandatory is False


def test_javascript_in_mandatory_section_is_not_java():
    requirements = RequirementExtractor().extract(
        "test",
        "Requisitos obrigatórios:\nJavaScript",
    )

    assert [item.name for item in requirements] == ["javascript"]
    assert requirements[0].mandatory is True
