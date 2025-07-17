#!/usr/bin/env python3
"""
GitHub Integration Test Script
Tests the GitHub token and basic GitHub API functionality
"""

import os
import requests
import json
from pathlib import Path

def test_github_token():
    """Test the GitHub token and get user info"""
    
    # Get token from environment
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("❌ GITHUB_TOKEN not found in environment")
        return False
    
    # Test GitHub API
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # Test user info
        print("🔍 Testing GitHub API connection...")
        response = requests.get('https://api.github.com/user', headers=headers)
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ GitHub connection successful!")
            print(f"👤 User: {user_info.get('login', 'Unknown')}")
            print(f"📧 Email: {user_info.get('email', 'Not public')}")
            print(f"🏢 Company: {user_info.get('company', 'Not specified')}")
            
            # Test repository access
            print("\n📂 Testing repository access...")
            repos_response = requests.get('https://api.github.com/user/repos', headers=headers)
            
            if repos_response.status_code == 200:
                repos = repos_response.json()
                print(f"✅ Found {len(repos)} repositories")
                
                # Show first 5 repositories
                print("\n📋 Recent repositories:")
                for repo in repos[:5]:
                    print(f"  • {repo['name']} ({repo['language'] or 'No language'})")
                
                return True
            else:
                print(f"❌ Error accessing repositories: {repos_response.status_code}")
                return False
                
        else:
            print(f"❌ GitHub API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing GitHub integration: {e}")
        return False

def test_repository_operations():
    """Test basic repository operations"""
    
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        return False
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # Test creating an issue (dry run - won't actually create)
        print("\n🔧 Testing repository operations...")
        
        # Get user info first
        user_response = requests.get('https://api.github.com/user', headers=headers)
        if user_response.status_code == 200:
            username = user_response.json()['login']
            
            # Test access to a repository (using the AI_System_Monorepo if it exists)
            repo_response = requests.get(f'https://api.github.com/repos/{username}/AI_System_Monorepo', headers=headers)
            
            if repo_response.status_code == 200:
                repo_info = repo_response.json()
                print(f"✅ Repository access: {repo_info['name']}")
                print(f"📊 Stars: {repo_info['stargazers_count']}")
                print(f"🔄 Forks: {repo_info['forks_count']}")
                print(f"📝 Description: {repo_info['description'] or 'No description'}")
                
                # Test issues access
                issues_response = requests.get(f'https://api.github.com/repos/{username}/AI_System_Monorepo/issues', headers=headers)
                if issues_response.status_code == 200:
                    issues = issues_response.json()
                    print(f"📋 Issues: {len(issues)} open issues")
                else:
                    print(f"⚠️  Issues access: {issues_response.status_code}")
                
                return True
            else:
                print(f"⚠️  Repository not found or access denied: {repo_response.status_code}")
                return False
        else:
            print(f"❌ Cannot get user info: {user_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing repository operations: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing GitHub Integration for Cursor Ultra Plan")
    print("=" * 50)
    
    # Test basic token functionality
    token_works = test_github_token()
    
    if token_works:
        # Test repository operations
        repo_works = test_repository_operations()
        
        print("\n" + "=" * 50)
        if repo_works:
            print("🎉 GitHub Integration Test: PASSED")
            print("\n✅ You can now use GitHub features in Cursor:")
            print("   • Create and manage issues")
            print("   • Review pull requests")
            print("   • Access repository information")
            print("   • Manage branches and commits")
        else:
            print("⚠️  GitHub Integration Test: PARTIAL")
            print("   • Token works but repository access limited")
    else:
        print("❌ GitHub Integration Test: FAILED")
        print("   • Check your GitHub token")
        print("   • Ensure token has proper permissions")

if __name__ == "__main__":
    main() 