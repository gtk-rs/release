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
        return
    for pr in content:
        if 'closed_at' in pr and pr['closed_at'] is not None:
            if compare_dates(pr['closed_at'], max_date):
                to_return.append(pr)
                total += 1
        elif 'updated_at' in pr:
            if compare_dates(pr['updated_at'], max_date):
                to_return.append(pr)
                total += 1

# This function tries to get as much github data as possible by running
# "parallel" requests.
def get_all_contents(url, state, max_date, token=None, recursive=True):
    headers = {
        'User-Agent': 'GuillaumeGomez',
        'Accept': 'application/vnd.github.v3+json',
    }
    params = {'sort': 'updated', 'state': state, 'per_page': 100,
              'direction': 'desc'}
    if token is not None:
        # Authentication to github.
        headers['Authorization'] = 'token %s' % token
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        if res.status_code == 403:
            # We reached the rate limit.
            if ('X-RateLimit-Limit' in res.headers and
                    'X-RateLimit-Remaining' in res.headers and
                    'X-RateLimit-Reset' in res.headers):
                raise Exception("Github rate limit exceeded...\n"
                                "X-RateLimit-Limit: %s\n"
                                "X-RateLimit-Remaining: %s\n"
                                "X-RateLimit-Reset: %s" %
                                (res.headers['X-RateLimit-Limit'],
                                 res.headers['X-RateLimit-Remaining'],
                                 res.headers['X-RateLimit-Reset']))
        raise Exception("Get request failed: '%s', got: [%s]: %s"
                        % (url, res.status_code, str(res.content)))
    content = res.json()
    to_return = []
    filter_data(content, to_return, max_date)
    if 'Link' not in res.headers or not recursive:
        # If there are no other pages, we can return the current content.
        if max_date is None:
            return content
        return to_return

    h = res.headers['Link']
    if h is None or len(h) != 1:
        return content

    next_page_url, last_page_url = get_next_pages_url(h)
    if len(last_page_url) < 10 or len(next_page_url) < 10:
        return content
    next_page = get_page_number(next_page_url)
    last_page = get_page_number(last_page_url)

    urls = [next_page_url]
    to_replace = "page=%s" % next_page
    next_page += 1
    while next_page <= last_page:
        requests.get(next_page_url.replace("&%s" % to_replace,
                                           "&page=%s" % next_page)
                                  .replace("?%s" % to_replace,
                                           "?page=%s" % next_page), headers=headers)
        if res.status_code != 200:
            break
        content = res.json()
        if filter_data(content, to_return, max_date) != len(content):
            break
        next_page += 1
    return to_return


class Github:
    def __init__(self, token):
        self.token = token

    def get_pull(self, repo_name, repo_owner, pull_number):
        return Repository(self.token, repo_name, repo_owner).get_pull(pull_number)

    def get_pulls(self, repo_name, repo_owner, state, max_date, only_merged=False):
        return Repository(self.token,
                          repo_name,
                          repo_owner).get_pulls(state,
                                                max_date,
                                                only_merged=only_merged)


class Repository:
    def __init__(self, token, name, owner):
        self.name = name
        self.token = token
        self.owner = owner

    def get_pulls(self, state, max_date, only_merged=False):
        prs = get_all_contents('https://api.github.com/repos/%s/%s/pulls'
                               % (self.owner, self.name),
                               state, max_date,
                               token=self.token)
        if prs is None:
            return []
        return [PullRequest(self.token, self.name, self.owner,
                            pr['number'],
                            pr['base']['ref'], pr['head']['ref'],
                            pr['head']['sha'], pr['title'],
                            pr['user']['login'], pr['state'],
                            pr['merged_at'], pr['closed_at']) for pr in prs
                            if (only_merged is False or
                                (pr['merged_at'] is not None and
                                 len(pr['merged_at']) > 0))]

    def get_pull(self, pull_number):
        pr = get_all_contents('https://api.github.com/repos/%s/%s/pulls/%s'
                              % (self.owner, self.name, pull_number),
                              'all', None,
                              token=self.token)
        if pr is None:
            return None
        return PullRequest(self.token, self.name, self.owner,
                           pull_number,
                           pr['base']['ref'], pr['head']['ref'],
                           pr['head']['sha'], pr['title'],
                           pr['user']['login'], pr['state'],
                           pr['merged_at'], pr['closed_at'])


# Represent a Github Pull Request.
class PullRequest:
    def __init__(self, token, repo_name, repo_owner,
                 pull_number, target_branch, from_branch, head_commit,
                 title, author, open_state, merged_at, closed_at):
        self.repo_name = repo_name
        self.token = token
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
        return ("https://github.com/%s/%s/pull/%s"
                % (self.repo_owner, self.repo_name, self.number))
