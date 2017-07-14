class Github:
    def __init__(self, token):
        self.token = token

    def get_pull(self, repo_name, repo_owner, pull_number):
        return Repository(self.token, repo_name, repo_owner).get_pull(pull_number)

    def get_pulls(self, repo_name, repo_owner, state, max_date):
        return Repository(self.token, repo_name, repo_owner).get_pulls(state, max_date)


class Repository:
    def __init__(self, token, name, owner):
        self.name = name
        self.token = token
        self.owner = owner

    def get_pulls(self, state, max_date, only_merged=False):
        prs = get_all_contents('https://api.github.com/repos/%s/%s/pulls'
                               % (self.owner, self.name), state, max_date,
                               token=self.token)
        if prs is None:
            return []
        return [PullRequest(self.token, self.name, self.owner,
                            pr['number'],
                            pr['base']['ref'], pr['head']['ref'],
                            pr['head']['sha'], pr['title'],
                            pr['user']['login'], pr['state'],
                            pr['merged_at'], pr['closed_at']) for pr in prs
                            if only_merged is False or len(pr['merged_at']) > 0]

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
