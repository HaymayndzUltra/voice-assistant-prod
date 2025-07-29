#!/usr/bin/env python3
"""
Test script for chunking functionality
"""

def test_chunking():
    # Test tasks
    tasks = [
        "Prepare the application for deployment. First, pull the latest changes from the 'main' branch. Next, install all dependencies using 'pip install -r requirements.txt'. Then, run all unit tests to ensure stability. Finally, create a production build of the application.",
        
        "Attempt to migrate the user database to the new schema. Before anything else, create a full backup of the current database and save it as 'backup.sql'. Then, run the 'migrate.py' script. If the migration fails, immediately restore from 'backup.sql' and log the error to 'migration_errors.log'. If successful, run the data verification script to confirm integrity.",
        
        "Perform the final preparations for the version 2.0 release. These are independent tasks: update the README.md file with the new features, clean up all temporary files from the '/logs' and '/temp' directories, and generate the final CHANGELOG.md from the git history.",
        
        "I-setup natin ang isang bagong Python project. Una, gumawa ka ng main directory na 'new_project'. Sa loob nito, gawa ka ng dalawang folder: 'src' at 'tests'. Pagkatapos, i-initialize mo ang git repository sa main directory. Sunod, gawa ka ng bagong virtual environment sa loob ng '.venv' folder. Panghuli, i-activate mo ito at i-install mo ang 'pytest' at 'requests' packages."
    ]
    
    print("=" * 80)
    print("CHUNKING TEST RESULTS")
    print("=" * 80)
    
    for i, task in enumerate(tasks, 1):
        print(f"\nTASK {i}:")
        print("-" * 40)
        print(f"Original: {task[:100]}...")
        print(f"Length: {len(task)} characters")
        
        try:
            from auto_detect_chunker import AutoDetectChunker
            chunker = AutoDetectChunker()
            chunks, analysis = chunker.auto_chunk(task)
            
            print(f"Chunks created: {len(chunks)}")
            print(f"Analysis: {analysis}")
            
            print("\nChunks:")
            for j, chunk in enumerate(chunks, 1):
                print(f"  {j}. {chunk[:80]}...")
                print(f"     Length: {len(chunk)} chars")
                
        except Exception as e:
            print(f"ERROR: {e}")
        
        print()

if __name__ == "__main__":
    test_chunking() 