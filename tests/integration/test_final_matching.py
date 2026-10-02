import pytest
from src.analysis.job_analyzer import JobAnalyzer
from src.domain.models import CandidateProfile, Job
from src.extraction.requirement_extractor import RequirementExtractor
from src.ingestion.collectors.serpapi_job_collector import SerpApiJobCollector


def profile(skills=None, filters=True):
    return CandidateProfile(id='synthetic', skills=skills or ['react','typescript','sql'],
        languages=[{'language':'Inglês','level':'B1'}],
        preferences={'job_filters': {'allowed_work_modes':['remote','hybrid'],
            'hybrid_locations':['Recife','Olinda','Paulista'],
            'remote_countries':['Brazil','Portugal']}} if filters else {})


def analyze(description='React obrigatório; TypeScript será um diferencial.', **kwargs):
    p=kwargs.pop('profile',None) or profile()
    fields=dict(id='synthetic',source='test',title='Frontend Developer Junior',company='Example',
                location='Brasil',work_mode='remote',description=description)
    fields.update(kwargs)
    job=Job(**fields)
    req=RequirementExtractor().extract(job.id,job.description)
    return JobAnalyzer().analyze(p,job,req)


@pytest.mark.parametrize('kwargs,status',[
    ({},'eligible'),
    ({'title':'Frontend Developer Senior'},'rejected'),
    ({'title':'Backend Developer Pleno'},'rejected'),
    ({'work_mode':'onsite','location':'Recife'},'rejected'),
    ({'work_mode':'hybrid','location':'Recife - PE'},'eligible'),
    ({'work_mode':'hybrid','location':'Olinda, Pernambuco'},'eligible'),
    ({'work_mode':'hybrid','location':'São Paulo - SP'},'rejected'),
    ({'work_mode':'hybrid','location':'Pernambuco'},'review'),
    ({'location':'Lisboa, Portugal'},'review'),
    ({'location':'Unknown'},'review'),
    ({'location':'USA'},'rejected'),
    ({'title':'Software Developer'},'review'),
])
def test_personal_eligibility(kwargs,status):
    analysis=analyze(**kwargs)
    assert analysis.breakdown['eligibility']['status']==status
    assert analysis.hard_blocker==(status!='eligible')


def test_senior_mentor_is_not_senior_vacancy():
    analysis=analyze('React obrigatório. Você terá mentoria de um desenvolvedor senior.')
    assert analysis.breakdown['eligibility']['status']=='eligible'
    assert analysis.breakdown['recommended_resume']=='frontend'


def test_portugal_explicit_brazil_and_restriction_precedence():
    a=analyze('React obrigatório. Aceitamos candidatos do Brasil.',location='Portugal')
    assert a.breakdown['eligibility']['status']=='eligible'
    b=analyze('React obrigatório. Worldwide. Must be based in Portugal.',location='Portugal')
    assert b.breakdown['eligibility']['status']=='review'


def test_conflicting_remote_and_hybrid_requires_review():
    assert analyze('React obrigatório. Modelo híbrido em Recife.').breakdown['eligibility']['status']=='review'


def test_negation_and_separate_mandatory_clause():
    a=analyze('Não é necessário Java; React obrigatório.')
    assert a.compatibility_score==100
    assert 'java' not in a.breakdown['requirements']
    assert not a.hard_blocker


def test_optional_clause_not_contaminated_by_other_mandatory():
    requirements=RequirementExtractor().extract('one','React obrigatório. Docker será um diferencial.')
    assert {r.name:r.mandatory for r in requirements}=={'react':True,'docker':False}


def test_alternative_satisfied_without_inventing_skill_and_sql_separate():
    p=profile(['python','sql'],filters=False)
    a=analyze('Python ou Java e SQL obrigatório.',profile=p)
    assert a.compatibility_score==100
    assert 'java' not in a.strengths+a.gaps+a.unknown_requirements
    assert 'sql' in a.strengths
    assert a.breakdown['alternatives_satisfied']==[{'alternative':'java','satisfied_by':'python'}]
    b=analyze('Python ou Java e SQL obrigatório.',profile=profile(['python'],filters=False))
    assert b.hard_blocker and 'sql' in b.gaps


def test_separate_java_requirement_is_not_waived():
    a=analyze('Python ou Java. Java obrigatório.',profile=profile(['python'],filters=False))
    assert 'java' in a.gaps and a.hard_blocker


def test_node_and_deno_recognized_without_javascript_false_positives():
    reqs=RequirementExtractor().extract('one','Node.js e Deno obrigatórios; React Native desejável.')
    names={r.name for r in reqs}
    assert {'node.js','deno','react_native'} <= names
    assert 'react' not in names


class Response:
    def __init__(self,data): self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data
class HTTP:
    def __init__(self,data): self.data=data; self.calls=[]
    def get(self,*args,**kwargs): self.calls.append(kwargs); return Response(self.data)


def test_serpapi_country_and_language_explicit():
    http=HTTP({'jobs_results':[]})
    SerpApiJobCollector('synthetic-key','junior',http_client=http,gl='pt',hl='pt').fetch_jobs()
    assert http.calls[0]['params']['gl']=='pt'
    assert http.calls[0]['params']['hl']=='pt'


def test_serpapi_known_empty_response_is_not_operational_failure():
    http=HTTP({'error':"Google hasn't returned any results for this query."})
    assert SerpApiJobCollector('synthetic-key','junior',http_client=http).fetch_jobs()==[]


@pytest.mark.parametrize('payload',[{'error':'Your account has run out of searches.'},[],{'jobs_results':'invalid'}])
def test_serpapi_failure_never_silently_becomes_no_jobs(payload):
    with pytest.raises(RuntimeError):
        SerpApiJobCollector('synthetic-key','junior',http_client=HTTP(payload)).fetch_jobs()
