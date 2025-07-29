# Maaari mong i-save ito bilang 'run_language_test.py' at i-execute gamit ang 'python3 run_language_test.py'

from workflow_memory_intelligence_fixed import ActionItemExtractor

def run_test():
    """
    Runs a language robustness and consistency test on the ActionItemExtractor.
    """
    extractor = ActionItemExtractor()

    print('🧠 LANGUAGE ROBUSTNESS & CONSISTENCY TEST')
    print('=' * 75)

    test_cases = [
        {
            'name': 'PURONG FILIPINO',
            'task': """Gawin natin ang bagong user authentication feature. Una sa lahat, i-update ang schema ng database para magkaroon ng 'users' table na may 'username' at 'password_hash' na mga column. Pagkatapos, bumuo ka ng isang API endpoint na '/login' na tumatanggap ng POST requests. Kung tama ang credentials, dapat itong magbalik ng isang JWT. Kung mali, dapat itong magbalik ng 401 Unauthorized error. Panghuli, gumawa ka ng isang simpleng login form sa frontend para i-test ang bagong endpoint."""
        },
        {
            'name': 'PURONG ENGLISH',
            'task': """Let's build the new user authentication feature. First of all, update the database schema to include a 'users' table with 'username' and 'password_hash' columns. Afterwards, create an API endpoint at '/login' that accepts POST requests. If the credentials are correct, it must return a JWT. If they are incorrect, it must return a 401 Unauthorized error. Finally, create a simple login form on the frontend to test the new endpoint."""
        },
        {
            'name': 'TAGLISH',
            'task': """I-build natin ang bagong user auth feature. First, i-update mo ang database schema, magdagdag ka ng 'users' table na may 'username' at 'password_hash' columns. Then, gawa ka ng API endpoint, sa '/login', na tatanggap ng POST requests. Kapag tama ang credentials, kailangan mag-return ito ng JWT. Kung mali naman, dapat 401 Unauthorized error ang i-return. Lastly, gawa ka ng simpleng login form sa frontend para ma-test natin yung endpoint."""
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f'\\n🎯 TEST {i}: {test["name"]}')
        print('-' * 50)
        
        # I-assume na ang extract_action_items ay ang method na ginagamit
        steps = extractor.extract_action_items(test['task'])
        
        print(f'📊 ANALYSIS: Extracted {len(steps)} actionable steps.')
        print('✅ DECOMPOSED PLAN:')
        for j, step in enumerate(steps, 1):
            print(f'  {j}. {step}')

    print('\\n' + '=' * 75)
    print('✅ LANGUAGE TEST COMPLETE')

if __name__ == "__main__":
    # Tiyaking ang iyong environment ay naka-set up nang tama para ma-import
    # ang workflow_memory_intelligence_fixed.
    # Maaaring kailanganin mong i-adjust ang PYTHONPATH.
    try:
        run_test()
    except ImportError:
        print("\\nERROR: Could not import 'ActionItemExtractor'.")
        print("Please ensure you are running this script from the root of your project")
        print("or that your PYTHONPATH is set correctly.")
    except Exception as e:
        print(f"\\nAn unexpected error occurred: {e}")
