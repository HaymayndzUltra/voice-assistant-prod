#!/usr/bin/env python3
"""
Docker Directory Duplicate Analysis
Identifies potential duplicate or similar folders and suggests cleanup.
"""

import os
import pathlib
import difflib
from collections import defaultdict
from typing import Dict, List, Tuple

def get_folder_info(folder_path: pathlib.Path) -> Dict:
    """Get basic information about a folder"""
    info = {
        'name': folder_path.name,
        'path': str(folder_path),
        'files': [],
        'has_dockerfile': False,
        'has_compose': False,
        'has_requirements': False,
        'file_count': 0
    }
    
    if folder_path.exists() and folder_path.is_dir():
        for file in folder_path.iterdir():
            if file.is_file():
                info['files'].append(file.name)
                info['file_count'] += 1
                
                if file.name.lower() == 'dockerfile':
                    info['has_dockerfile'] = True
                elif file.name.lower() == 'docker-compose.yml':
                    info['has_compose'] = True
                elif file.name.lower() == 'requirements.txt':
                    info['has_requirements'] = True
    
    return info

def find_similar_names(folders: List[str], threshold: float = 0.6) -> List[Tuple[str, str, float]]:
    """Find folders with similar names"""
    similar_pairs = []
    
    for i, folder1 in enumerate(folders):
        for folder2 in folders[i+1:]:
            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(None, folder1, folder2).ratio()
            
            if similarity >= threshold:
                similar_pairs.append((folder1, folder2, similarity))
    
    return sorted(similar_pairs, key=lambda x: x[2], reverse=True)

def identify_potential_duplicates() -> Dict:
    """Identify potential duplicate folders"""
    docker_dir = pathlib.Path("docker")
    
    # Get all folders
    folders = [d.name for d in docker_dir.iterdir() if d.is_dir()]
    
    # Group by common patterns
    patterns = defaultdict(list)
    
    for folder in folders:
        # Group by base name (without _agent suffix)
        base_name = folder.replace('_agent', '').replace('_service', '')
        patterns[base_name].append(folder)
    
    # Find groups with multiple matches
    potential_duplicates = {}
    for base_name, group in patterns.items():
        if len(group) > 1:
            potential_duplicates[base_name] = group
    
    # Find similar names
    similar_names = find_similar_names(folders)
    
    # Get detailed info for analysis
    folder_info = {}
    for folder in folders:
        folder_path = docker_dir / folder
        folder_info[folder] = get_folder_info(folder_path)
    
    return {
        'potential_duplicates': potential_duplicates,
        'similar_names': similar_names,
        'folder_info': folder_info,
        'total_folders': len(folders)
    }

def analyze_duplicates():
    """Main analysis function"""
    print("🔍 Analyzing Docker Directory for Duplicates")
    print("=" * 60)
    
    analysis = identify_potential_duplicates()
    
    print(f"📊 Total folders analyzed: {analysis['total_folders']}")
    print()
    
    # Report potential duplicates
    if analysis['potential_duplicates']:
        print("🚨 POTENTIAL DUPLICATE GROUPS:")
        print("-" * 40)
        
        for base_name, group in analysis['potential_duplicates'].items():
            print(f"\n📁 Base pattern: '{base_name}'")
            print(f"   Folders: {', '.join(group)}")
            
            # Analyze each folder in the group
            for folder in group:
                info = analysis['folder_info'][folder]
                print(f"   • {folder}:")
                print(f"     Files: {info['file_count']} | Dockerfile: {'✅' if info['has_dockerfile'] else '❌'} | Compose: {'✅' if info['has_compose'] else '❌'}")
    else:
        print("✅ No obvious pattern-based duplicates found")
    
    print("\n" + "=" * 60)
    
    # Report similar names
    if analysis['similar_names']:
        print("⚠️  SIMILAR FOLDER NAMES:")
        print("-" * 40)
        
        for folder1, folder2, similarity in analysis['similar_names']:
            print(f"\n🔗 {similarity:.1%} similar:")
            print(f"   • {folder1}")
            print(f"   • {folder2}")
            
            info1 = analysis['folder_info'][folder1]
            info2 = analysis['folder_info'][folder2]
            
            print(f"   Files: {info1['file_count']} vs {info2['file_count']}")
            print(f"   Docker: {'✅' if info1['has_dockerfile'] else '❌'} vs {'✅' if info2['has_dockerfile'] else '❌'}")
    else:
        print("✅ No significantly similar folder names found")
    
    print("\n" + "=" * 60)
    print("💡 CLEANUP RECOMMENDATIONS:")
    print("-" * 40)
    
    # Generate recommendations
    recommendations = []
    
    # Check for empty or incomplete folders
    for folder, info in analysis['folder_info'].items():
        if info['file_count'] == 0:
            recommendations.append({
                'folder': folder,
                'action': 'DELETE',
                'reason': 'Folder is empty',
                'priority': 'HIGH'
            })
        elif not info['has_dockerfile'] and not info['has_compose']:
            recommendations.append({
                'folder': folder,
                'action': 'REVIEW',
                'reason': 'Missing both Dockerfile and docker-compose.yml',
                'priority': 'MEDIUM'
            })
    
    # Check for obvious duplicates in patterns
    for base_name, group in analysis['potential_duplicates'].items():
        if len(group) == 2:
            # Compare the two folders
            folder1, folder2 = group
            info1 = analysis['folder_info'][folder1]
            info2 = analysis['folder_info'][folder2]
            
            # Suggest keeping the more complete one
            if info1['file_count'] > info2['file_count']:
                recommendations.append({
                    'folder': folder2,
                    'action': 'CONSIDER DELETING',
                    'reason': f'Less complete than {folder1} ({info2["file_count"]} vs {info1["file_count"]} files)',
                    'priority': 'MEDIUM'
                })
            elif info2['file_count'] > info1['file_count']:
                recommendations.append({
                    'folder': folder1,
                    'action': 'CONSIDER DELETING', 
                    'reason': f'Less complete than {folder2} ({info1["file_count"]} vs {info2["file_count"]} files)',
                    'priority': 'MEDIUM'
                })
            else:
                recommendations.append({
                    'folder': f'{folder1} OR {folder2}',
                    'action': 'MANUAL REVIEW',
                    'reason': f'Similar folders with same file count ({info1["file_count"]} files each)',
                    'priority': 'LOW'
                })
    
    # Display recommendations
    if recommendations:
        for rec in sorted(recommendations, key=lambda x: {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}[x['priority']], reverse=True):
            priority_icon = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[rec['priority']]
            print(f"\n{priority_icon} {rec['priority']} PRIORITY:")
            print(f"   Folder: {rec['folder']}")
            print(f"   Action: {rec['action']}")
            print(f"   Reason: {rec['reason']}")
    else:
        print("\n✅ No cleanup recommendations - all folders appear necessary")
    
    print(f"\n{'='*60}")
    print("📋 SUMMARY:")
    print(f"   Total folders: {analysis['total_folders']}")
    print(f"   Potential duplicates: {len(analysis['potential_duplicates'])}")
    print(f"   Similar names: {len(analysis['similar_names'])}")
    print(f"   Cleanup recommendations: {len(recommendations)}")

if __name__ == "__main__":
    analyze_duplicates()
