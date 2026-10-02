"""Conservative eligibility rules for the personal profile; uncertainty is explicit."""
import re
import unicodedata


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').lower()) if not unicodedata.combining(c))


def contains(pattern, value):
    return bool(re.search(pattern, norm(value)))


class EligibilityEvaluator:
    def evaluate(self, profile, job, requirements=None):
        cv = self._recommend_cv(job, requirements or [])
        filters = profile.preferences.get('job_filters')
        if not filters:
            return {}, False, cv
        reasons, statuses = [], []
        for status, reason in (self._seniority(job), self._role(job), self._location(job, filters), self._restrictions(job, profile)):
            if reason:
                reasons.append(reason)
            statuses.append(status)
        status = 'rejected' if 'rejected' in statuses else 'review' if 'review' in statuses else 'eligible'
        if status == 'eligible':
            reasons.append('Senioridade Júnior e modalidade/localização compatíveis com os filtros pessoais.')
        return {'status': status, 'reasons': reasons}, status != 'eligible', cv

    @staticmethod
    def _seniority(job):
        # Senior colleagues or mentors in the body are not the vacancy's level.
        text = norm(f'{job.title} {job.seniority or ""}')
        if re.search(r'\b(senior|sr|lead|principal|staff|especialista|gerente|head|director|diretor|arquiteto|architect)\b', text):
            return 'rejected', 'Senior/Lead ou cargo acima do nível Júnior desejado.'
        if re.search(r'\b(pleno|mid|mid-level)\b', text):
            return 'rejected', 'Senioridade Pleno acima do nível Júnior desejado.'
        if re.search(r'\b(estagio|estagiario|intern|internship|trainee)\b', text):
            return 'review', 'Estágio/trainee: interesse e disponibilidade não foram confirmados.'
        if re.search(r'\b(junior|jr|entry.level)\b', text):
            return 'eligible', ''
        return 'review', 'Senioridade ausente ou não especificada claramente.'

    @staticmethod
    def _role(job):
        title = norm(job.title)
        if re.search(r'\b(qa|tester|devops|suporte|support|designer|data scientist|cientista de dados)\b', title):
            return 'rejected', 'Função fora das buscas de desenvolvimento Frontend/Backend/Full Stack.'
        if not re.search(r'\b(developer|desenvolvedor|desenvolvedora|programador|programadora|frontend|front.end|backend|back.end|full.stack|software engineer|engenheir[oa] de software)\b', title):
            return 'review', 'Função não identificada com segurança como desenvolvimento web/software.'
        return 'eligible', ''

    @staticmethod
    def _location(job, filters):
        raw = norm(job.work_mode)
        aliases = {'remoto':'remote','remota':'remote','hibrido':'hybrid','hibrida':'hybrid','presencial':'onsite','on-site':'onsite'}
        mode = aliases.get(raw, raw)
        text = norm(f'{job.title} {job.location or ""} {job.description}')
        loc = norm(job.location)
        if mode == 'remote' and re.search(r'\b(hibrid[oa]|hybrid|office attendance|dias presenciais)\b', norm(job.description)):
            return 'review', 'Anúncio marcado remoto, mas descreve presença/híbrido: confirmar modalidade real.'
        if mode not in ('remote','hybrid','onsite'):
            # Hybrid takes precedence when office days and remote are both mentioned.
            if re.search(r'\b(hibrid[oa]|hybrid)\b', text):
                mode = 'hybrid'
            elif re.search(r'\b(remot[oa]|remote|home office)\b', text):
                mode = 'remote'
            elif re.search(r'\b(presencial|on.site|onsite)\b', text):
                mode = 'onsite'
            else:
                return 'review', 'Modo de trabalho não especificado com segurança.'
        allowed = [aliases.get(norm(x), norm(x)) for x in filters.get('allowed_work_modes', [])]
        if mode not in allowed:
            return 'rejected', f'Modalidade {mode} (presencial quando onsite) fora das preferências.'
        if mode == 'hybrid':
            if not loc or loc in ('brazil','brasil','pernambuco','pe'):
                return 'review', 'Município da vaga híbrida não confirmado.'
            cities = [norm(x) for x in filters.get('hybrid_locations', [])]
            segments = [s.strip() for s in re.split(r'[,/;]', loc)]
            matches = any(re.match(r'^'+re.escape(city)+r'(?:\s*-|\s*\(|$)', segment) for city in cities for segment in segments)
            if 'grande recife' in loc or 'regiao metropolitana do recife' in loc:
                matches = True
            if matches:
                return 'eligible', ''
            return 'rejected', 'Vaga híbrida fora da Grande Recife: '+str(job.location)
        if mode == 'remote':
            countries = {norm(c) for c in filters.get('remote_countries', [])}
            br_allowed = bool(countries & {'brazil','brasil'})
            pt_allowed = 'portugal' in countries
            portugal = bool(re.search(r'\b(portugal|lisboa|lisbon|porto)\b', loc+' '+norm(job.company)))
            # Restrictions must take priority over a generic 'worldwide' statement.
            restriction = re.search(r'\b(residen\w*|residir|basead\w*|based|autorizacao|permissao|work permit|right to work|eligible to work)\b.{0,90}\b(portugal|europe|europa|ue|eu|united states|usa|estados unidos)\b', text)
            restriction = restriction or re.search(r'\b(eu|european|portuguese|us)\s+(citizens|residents|work permit)\b|\b(us|usa|eu|europe|portugal)[ -]only\b',text)
            if restriction:
                return 'review', 'Restrição de residência/autorização estrangeira exige revisão; candidato no Brasil.'
            explicit_brazil = bool(re.search(r'\b(from brazil|based in brazil|a partir do brasil|residentes no brasil|candidatos do brasil|anywhere in the world|worldwide|global remote)\b',text))
            if portugal:
                if not pt_allowed:
                    return 'rejected', 'Portugal fora dos países configurados.'
                if explicit_brazil and br_allowed:
                    return 'eligible', ''
                return 'review', 'Remoto Portugal: confirmar contratação de pessoa trabalhando a partir do Brasil.'
            brazil = bool(re.search(r'\b(brasil|brazil)\b',loc))
            brazil = brazil or bool(re.search(r'\b(remot[oa]|remote)\b.{0,40}\b(brasil|brazil)\b',text))
            if br_allowed and (brazil or explicit_brazil):
                return 'eligible', ''
            if re.search(r'\b(united states|usa|us only|estados unidos|canada|united kingdom|uk only)\b',loc):
                return 'rejected', 'País remoto fora de Brasil/Portugal ou contratação local estrangeira.'
            return 'review', 'País/elegibilidade para trabalho remoto a partir do Brasil não confirmado.'
        return 'eligible', ''

    @staticmethod
    def _restrictions(job, profile):
        text = norm(job.description)
        levels = {norm(x.get('level')) for x in profile.languages}
        if 'b1' in levels and re.search(r'\b(ingles\s+(avancado|fluente)|fluent\s+english|advanced\s+english|english\s+(c1|c2|b2))\b',text):
            return 'review', 'Exigência de inglês acima de B1: confirmar se é obrigatória e compatível.'
        return 'eligible', ''

    @staticmethod
    def _recommend_cv(job, requirements):
        title = norm(job.title)
        if re.search(r'full[ -]?stack',title): return 'full_stack'
        if re.search(r'front[ -]?end',title): return 'frontend'
        if re.search(r'back[ -]?end',title): return 'backend'
        names = {norm(r.name) for r in requirements}
        if names & {'react','html','css'} and not names & {'node.js','deno','sql'}: return 'frontend'
        if names & {'node.js','deno','sql'} and not names & {'react','html','css'}: return 'backend'
        return 'full_stack'
