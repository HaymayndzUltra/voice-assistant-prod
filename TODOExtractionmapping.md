🔥 How to Integrate the Ultimate TODO Extraction Mapping
1. Replace the current minimal mappings in your ActionItemExtractor with the “maximal” dictionaries below.
Step 1: Drop this inside your __init__ (replace the old ones):

# --- Replace your current dicts with these FULL sets ---
self.action_concepts = {
    'CREATE': [
        'create', 'build', 'gumawa', 'magbuild', 'gawa', 'make', 'new', 'i-create', 'scaffold', 'setup',
        'generate', 'instantiate', 'compose', 'mag-generate', 'add', 'dagdag', 'add file', 'add folder',
        'magdagdag', 'add module'
    ],
    'UPDATE': [
        'update', 'edit', 'baguhin', 'palitan', 'revise', 'amend', 'modify', 'tweak', 'refactor', 'change',
        'i-update', 'i-edit', 'revamp', 'rework', 'rename'
    ],
    'DELETE': [
        'delete', 'remove', 'alisin', 'burahin', 'drop', 'erase', 'destroy', 'magdelete', 'uninstall',
        'i-delete', 'tanggalin', 'bura', 'purge', 'clean', 'clear'
    ],
    'IMPLEMENT': [
        'implement', 'ipatupad', 'apply', 'mag-implement', 'i-implement', 'isagawa', 'i-apply', 'magpatupad',
        'execute', 'mag-execute', 'i-execute', 'gamitin', 'deploy', 'ilunsad', 'paganahin'
    ],
    'DEVELOP': [
        'develop', 'dev', 'magdev', 'i-develop', 'gumawa', 'i-dev', 'design', 'enhance', 'improve', 'dagdagan',
        'expand', 'i-enhance', 'magdagdag', 'i-design', 'idisenyo', 'disenyo'
    ],
    'TEST': [
        'test', 'itest', 'i-test', 'subukan', 'run test', 'check', 'magtest', 'i-check', 'verify', 'beripikahin',
        'suriin', 'mag-subok', 'unit test', 'integration test', 'validate', 'i-validate', 'mag-validate'
    ],
    'VALIDATE': [
        'validate', 'mag-validate', 'i-validate', 'patunayan', 'beripikahin', 'i-verify', 'siguruhin', 'lint',
        'run linter', 'check code', 'maglint', 'i-lint'
    ],
    'DEPLOY': [
        'deploy', 'mag-deploy', 'i-deploy', 'ilunsad', 'release', 'publish', 'push to prod', 'rollout', 'launch',
        'deploy to server', 'deploy to production', 'roll-out'
    ],
    'MERGE': [
        'merge', 'i-merge', 'pagsamahin', 'mag-merge', 'combine', 'pull request', 'PR', 'rebase', 'integrate',
        'git merge', 'i-integrate'
    ],
    'REVERT': [
        'revert', 'mag-revert', 'i-revert', 'bawiin', 'rollback', 'undo', 'cancel changes', 'reverse', 'reset',
        'i-reset'
    ],
    'COMMIT': [
        'commit', 'i-commit', 'isave', 'mag-commit', 'save changes', 'add commit', 'git commit', 'log changes',
        'commit changes'
    ],
    'PUSH': [
        'push', 'i-push', 'mag-push', 'upload', 'push to repo', 'git push', 'publish', 'send'
    ],
    'PULL': [
        'pull', 'i-pull', 'mag-pull', 'download', 'pull from repo', 'git pull', 'fetch'
    ],
    'RETURN': [
        'return', 'ibalik', 'magbalik', 'rollback', 'i-return', 'restore', 'revert changes'
    ],
    'ACCEPT': [
        'accept', 'tanggapin', 'i-accept', 'mag-accept', 'approve', 'aprubahan', 'merge PR', 'i-approve'
    ],
    'REJECT': [
        'reject', 'i-reject', 'tanggihan', 'i-deny', 'deny', 'bawiin', 'close PR', 'decline'
    ],
    'FEATURE': [
        'feature', 'add feature', 'module', 'function', 'authentication', 'auth', 'login', 'signup', 'modulo',
        'i-feature', 'mag-feature', 'add functionality', 'add module', 'feature request'
    ],
    'DOCUMENT': [
        'document', 'docs', 'mag-docs', 'add docs', 'gawing dokumento', 'add documentation', 'i-doc', 'mag-document',
        'create docs', 'update docs', 'write docs', 'docstring'
    ],
    'INSTALL': [
        'install', 'mag-install', 'i-install', 'setup', 'mag-setup', 'i-setup', 'pip install', 'npm install',
        'add dependency', 'install dependency', 'add package', 'magdagdag ng package'
    ],
    'CONFIGURE': [
        'configure', 'i-configure', 'mag-configure', 'settings', 'set up', 'setup', 'i-setup', 'adjust', 'i-adjust',
        'ayusin', 'iset', 'i-set', 'baguhin ang settings', 'configuration'
    ],
    'CONNECT': [
        'connect', 'link', 'integrate', 'associate', 'join', 'i-connect', 'mag-connect', 'link up'
    ],
    'DISCONNECT': [
        'disconnect', 'unlink', 'detach', 'i-disconnect', 'mag-disconnect', 'unplug', 'tanggalin ang koneksyon'
    ],
    'OPEN': [
        'open', 'launch', 'start', 'run', 'execute', 'i-open', 'mag-open', 'simulan', 'buksan'
    ],
    'CLOSE': [
        'close', 'shut', 'exit', 'terminate', 'i-close', 'mag-close', 'isara', 'stop'
    ],
}





self.sequential_markers = {
    # English
    'first of all': ['SEQ_1'],
    'first': ['SEQ_1'],
    'step one': ['SEQ_1'],
    'initially': ['SEQ_1'],
    'to begin': ['SEQ_1'],
    'before anything else': ['SEQ_1'],
    'set up': ['SEQ_1'],
    'prepare': ['SEQ_1'],
    'at the start': ['SEQ_1'],
    'in the beginning': ['SEQ_1'],
    'primarily': ['SEQ_1'],
    'starting with': ['SEQ_1'],
    'second': ['SEQ_2'],
    'next': ['SEQ_2'],
    'after that': ['SEQ_2'],
    'afterwards': ['SEQ_2'],
    'subsequently': ['SEQ_2'],
    'continue': ['SEQ_2'],
    'step two': ['SEQ_2'],
    'move on': ['SEQ_2'],
    'followed by': ['SEQ_2'],
    'third': ['SEQ_3'],
    'then': ['SEQ_3'],
    'afterward': ['SEQ_3'],
    'step three': ['SEQ_3'],
    'later': ['SEQ_3'],
    'proceed': ['SEQ_3'],
    'finally': ['SEQ_4'],
    'lastly': ['SEQ_4'],
    'in the end': ['SEQ_4'],
    'at the end': ['SEQ_4'],
    'wrap up': ['SEQ_4'],
    'complete': ['SEQ_4'],
    'ultimately': ['SEQ_4'],
    'eventually': ['SEQ_4'],
    'finish up': ['SEQ_4'],
    'step four': ['SEQ_4'],
    # Filipino/Taglish
    'una sa lahat': ['SEQ_1'],
    'una,': ['SEQ_1'],
    'simula': ['SEQ_1'],
    'umpisa': ['SEQ_1'],
    'maghanda': ['SEQ_1'],
    'sa simula': ['SEQ_1'],
    'panimula': ['SEQ_1'],
    'unang-una': ['SEQ_1'],
    'pangalawa': ['SEQ_2'],
    'ikalawa': ['SEQ_2'],
    'sunod': ['SEQ_2'],
    'kasunod': ['SEQ_2'],
    'pagkatapos': ['SEQ_2'],
    'tapos nito': ['SEQ_2'],
    'sumunod': ['SEQ_2'],
    'ituloy': ['SEQ_2'],
    'next step': ['SEQ_2'],
    'pangatlo': ['SEQ_3'],
    'ikatlo': ['SEQ_3'],
    'pagkalipas': ['SEQ_3'],
    'pangatlong hakbang': ['SEQ_3'],
    'sa wakas': ['SEQ_4'],
    'panghuli': ['SEQ_4'],
    'pahuli': ['SEQ_4'],
    'sa dulo': ['SEQ_4'],
    'tapusin': ['SEQ_4'],
    'wakasan': ['SEQ_4'],
    'final step': ['SEQ_4'],
}




self.conditional_markers = {
    # English logic triggers
    'if': ['[IF]'],
    'when': ['[IF]'],
    'once': ['[IF]'],
    'whenever': ['[IF]'],
    'provided': ['[IF]'],
    'unless': ['[IF_NOT]'],
    'as long as': ['[IF]'],
    'in case': ['[IF]'],
    'assuming': ['[IF]'],
    'given that': ['[IF]'],
    'even if': ['[IF]'],
    'only if': ['[IF]'],
    'where': ['[IF]'],
    'on condition that': ['[IF]'],
    'in the event that': ['[IF]'],
    'suppose': ['[IF]'],
    'supposing': ['[IF]'],
    'so long as': ['[IF]'],
    # Filipino/Taglish logic triggers
    'kung': ['[IF]'],
    'kapag': ['[IF]'],
    'pag': ['[IF]'],
    'sakali': ['[IF]'],
    'sakaling': ['[IF]'],
    'maliban kung': ['[IF_NOT]'],
    'hangga\'t': ['[IF]'],
    'basta': ['[IF]'],
    'pagka': ['[IF]'],
    'kung sakali': ['[IF]'],
    'sakaling hindi': ['[IF_NOT]'],
    # Coding-specific results
    'success': 'CORRECT',
    'passed': 'CORRECT',
    'correct': 'CORRECT',
    'right': 'CORRECT',
    'true': 'CORRECT',
    'valid': 'CORRECT',
    'build success': 'CORRECT',
    'test pass': 'CORRECT',
    'pass': 'CORRECT',
    'green': 'CORRECT',
    'ok': 'CORRECT',
    'ayos': 'CORRECT',
    'resolved': 'CORRECT',
    'works': 'CORRECT',
    'fail': 'INCORRECT',
    'failed': 'INCORRECT',
    'incorrect': 'INCORRECT',
    'wrong': 'INCORRECT',
    'error': 'INCORRECT',
    'false': 'INCORRECT',
    'invalid': 'INCORRECT',
    'build failed': 'INCORRECT',
    'test fail': 'INCORRECT',
    'red': 'INCORRECT',
    'bug': 'INCORRECT',
    'issue': 'INCORRECT',
    'palpak': 'INCORRECT',
    'hindi pwede': 'INCORRECT',
    # Filipino outcome terms
    'tama': 'CORRECT',
    'mali': 'INCORRECT',
    'pumasa': 'CORRECT',
    'bumagsak': 'INCORRECT',
    'tagumpay': 'CORRECT',
    'palpak': 'INCORRECT',
    'pwede': 'CORRECT',
    'bawal': 'INCORRECT',
    'pumalya': 'INCORRECT',
    'pasado': 'CORRECT',
    'bagsak': 'INCORRECT',
    'ayos': 'CORRECT',
    'ayos na': 'CORRECT',
    'hindi gumana': 'INCORRECT',
}




