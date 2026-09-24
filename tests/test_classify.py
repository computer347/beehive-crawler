from crawler.classify import student_type, country_city, fields_for, required_languages

def test_student_types():
    assert student_type("Software Engineering Intern") == "Internship"
    assert student_type("Summer Trainee 2027, Electrical Design") == "Summer job"
    assert student_type("Kesätyöntekijä, sähkösuunnittelu") == "Summer job"
    assert student_type("Examensarbete: batterimodellering") == "Thesis"
    assert student_type("Working Student - Data") == "Part-time"
    assert student_type("International Trainee - Business Engineer") == "Graduate"

def test_not_student_roles():
    for t in ["Senior Software Engineer", "Internal Audit Specialist", "Engineering Manager",
              "Arbetsmarknadshandläggare till Intern service", "Riskanalytiker med fokus på intern kontroll",
              "Vill du jobba som svetsare? Trainee-program för dig", "CNC-operatör trainee"]:
        assert student_type(t) is None, t

def test_geography():
    assert country_city("Espoo, Finland") == ("FI", "Espoo")
    assert country_city("København")[0] == "DK"
    assert country_city("London, UK") == ("", "")

def test_fields_and_languages():
    assert "Computer Science" in fields_for("Sommerjobb som utvikler", "")
    assert "Swedish" in required_languages("Vi söker dig som har goda kunskaper i programmering och som vill arbeta med oss på vårt kontor. Du har en utbildning inom el eller data och är intresserad av att lära dig mer om hur vi arbetar med system och kunder varje dag.")
