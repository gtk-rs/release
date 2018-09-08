from datetime import date
# pip3 install requests
import requests

def compare_dates(gh_date, d):
    if gh_date is None or len(gh_date) < 1:
        return False
    gh_date = gh_date.split('T')[0].split('-')
    year = int(gh_date[0])
    month = int(gh_date[1])
    day = int(gh_date[2])

    return date(year, month, day) >= d


def get_page_number(url):
    parts = url.split('?')[-1].split('&')
    for part in parts:
        if part.startswith('page='):
            try:
                return int(part.split('=')[-1])
            except:
                break
    return 1


def get_next_pages_url(link):
    parts = link.split(',')
    subs = []
    for part in parts:
        subs.append(part.split(';'))
    next_page_url = ''
    last_page_url = ''
    for sub in subs:
        if len(sub) != 2:
            continue
        if sub[1].endswith('"next"'):
            next_page_url = sub[0][1:-1]
        elif sub[1].endswith('"last"'):
            last_page_url = sub[0][1:-1]
    return next_page_url, last_page_url


def filter_data(content, to_return, max_date):
    total = 0
    if content.__class__.__name__ == 'dict':
        return 0
    for pr in content:
        if 'closed_at' in pr and pr['closed_at'] is not None:
            if compare_dates(pr['closed_at'], max_date):
                to_return.append(pr)
                total += 1
        elif 'updated_at' in pr:
            if compare_dates(pr['updated_at'], max_date):
                to_return.append(pr)
                total += 1
    return total



def get_url_data(url, headers, params):
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        if res.status_code == 403:
            # We reached the rate limit.
            if ('X-RateLimit-Limit' in res.headers and
                    'X-RateLimit-Remaining' in res.headers and
                    'X-RateLimit-Reset' in res.headers):
                raise Exception("Github rate limit exceeded...\n"
                                "X-RateLimit-Limit: {}\n"
                                "X-RateLimit-Remaining: {}\n"
                                "X-RateLimit-Reset: {}".format(res.headers['X-RateLimit-Limit'],
                                                               res.headers['X-RateLimit-Remaining'],
                                                               res.headers['X-RateLimit-Reset']))
        raise Exception("Get request failed: '{}', got: [{}]: {}".format(url,
                                                                         res.status_code,
                                                                         str(res.content)))
    return res


# This function tries to get as much github data as possible by running
# "parallel" requests.
def get_all_contents(url, state=None, max_date=None, token=None, recursive=True, params={}):
    headers = {
        'User-Agent': 'GuillaumeGomez',
        'Accept': 'application/vnd.github.v3+json',
    }
    params['per_page'] = 100
    if state is not None:
        params['sort'] = 'updated'
        params['state'] = state
        params['direction'] = 'desc'
    if token is not None:
        # Authentication to github.
        headers['Authorization'] = 'token {}'.format(token)
    res = get_url_data(url, headers, params)
    content = res.json()
    to_return = []
    if max_date is not None:
        if filter_data(content, to_return, max_date) < 100:
            return to_return
    else:
        for x in content:
            to_return.append(x)
    if 'Link' not in res.headers or not recursive:
        # If there are no other pages, we can return the current content.
        return to_return

    h = res.headers['Link']
    if h is None or len(h) < 1:
        return content

    next_page_url, last_page_url = get_next_pages_url(h)
    if len(last_page_url) < 10 or len(next_page_url) < 10:
        return to_return
    next_page = get_page_number(next_page_url)
    last_page = get_page_number(last_page_url)
    to_replace = "page={}".format(next_page)

    while next_page <= last_page:
        res = get_url_data(next_page_url.replace("&{}".format(to_replace),
                                                 "&page={}".format(next_page)),
                           headers,
                           None)
        if res.status_code != 200:
            break
        content = res.json()
        if max_date is not None:
            if filter_data(content, to_return, max_date) < 100:
                break
        else:
            for x in content:
                to_return.append(x)
        next_page += 1
    return to_return


class Github:
    def __init__(self, token):
        self.token = token

    def get_pull(self, repo_name, repo_owner, pull_number):
        return Repository(self, repo_name, repo_owner).get_pull(pull_number)

    def get_pulls(self, repo_name, repo_owner, state, max_date, only_merged=False):
        return Repository(self,
                          repo_name,
                          repo_owner).get_pulls(state,
                                                max_date,
                                                only_merged=only_merged)

    def get_organization(self, organization_name):
        return Organization(self, organization_name)


class Organization:
    def __init__(self, gh_obj, name):
        self.gh_obj = gh_obj
        self.name = name

    def get_repositories(self):
        repos = get_all_contents('https://api.github.com/orgs/{}/repos'.format(self.name),
                                 token=self.gh_obj.token)
        if repos is None:
            return []
        return [Repository(self.gh_obj, repo['name'], repo['owner']['login'])
                for repo in repos]


class Repository:
    def __init__(self, gh_obj, name, owner):
        self.name = name
        self.gh_obj = gh_obj
        self.owner = owner

    def get_pulls(self, state, max_date, only_merged=False):
        prs = get_all_contents('https://api.github.com/repos/{}/{}/pulls'.format(self.owner,
                                                                                 self.name),
                               state, max_date,
                               token=self.gh_obj.token)
        if prs is None:
            return []
        return [PullRequest(self.gh_obj, self.name, self.owner,
                            pr['number'],
                            pr['base']['ref'], pr['head']['ref'],
                            pr['head']['sha'], pr['title'],
                            pr['user']['login'], pr['state'],
                            pr['merged_at'], pr['closed_at']) for pr in prs
                            if (only_merged is False or
                                (pr['merged_at'] is not None and
                                 len(pr['merged_at']) > 0))]

    def get_pull(self, pull_number):
        pr = get_all_contents('https://api.github.com/repos/{}/{}/pulls/{}'.format(self.owner,
                                                                                   self.name,
                                                                                   pull_number),
                              'all', None,
                              token=self.gh_obj.token)
        if pr is None:
            return None
        return PullRequest(self.gh_obj, self.name, self.owner,
                           pull_number,
                           pr['base']['ref'], pr['head']['ref'],
                           pr['head']['sha'], pr['title'],
                           pr['user']['login'], pr['state'],
                           pr['merged_at'], pr['closed_at'])

    def get_commits(self, branch, since, until):
        commits = get_all_contents(
            'https://api.github.com/repos/{}/{}/commits'.format(self.owner, self.name),
            token=self.gh_obj.token,
            params={'sha': branch,
                    'since': '{}-{:01d}-{:01d}T00:00:00Z'.format(since.year, since.month,
                                                                 since.day),
                    'until': '{}-{:01d}-{:01d}T00:00:00Z'.format(until.year, until.month,
                                                                 until.day)})
        if commits is None:
            return []
        return [Commit(x['commit']['author']['name'], x['commit']['committer']['name'],
                       x['sha'], x['commit']['message'])
                for x in commits]


class Commit:
    def __init__(self, author, committer, sha, message):
        self.author = author
        self.committer = committer
        self.sha = sha
        self.message = message


# Represent a Github Pull Request.
class PullRequest:
    def __init__(self, gh_obj, repo_name, repo_owner,
                 pull_number, target_branch, from_branch, head_commit,
                 title, author, open_state, merged_at, closed_at):
        self.repo_name = repo_name
        self.gh_obj = gh_obj
        self.repo_owner = repo_owner
        self.number = pull_number
        self.target_branch = target_branch
        self.from_branch = from_branch
        self.head_commit = head_commit
        self.title = title
        self.author = author
        self.open_state = open_state
        self.merged_at = merged_at
        if self.merged_at is None:
            self.merged_at = ''
        self.closed_at = closed_at
        if self.closed_at is None:
            self.closed_at = ''

    def get_url(self):
        return ("https://github.com/{}/{}/pull/{}".format(self.repo_owner,
                                                          self.repo_name,
                                                          self.number))
