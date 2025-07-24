#!/usr/bin/env python3
"""
O3 Pro Max Batch Fix Script - Step 1: Automated Syntax Cleanup
Quick-n-dirty patch: comment out stray 'self.' lines so the
interpreter can at least import the modules again. Real fixes should
replace them with meaningful logic later.
"""
import pathlib
import re
import sys
import os

ROOT = pathlib.Path(__file__).resolve().parents[0] / "main_pc_code"
pattern = re.compile(r'^\s*self\.\s*$')

def fix_stray_self_statements():
    """Fix all stray 'self.' statements in Python files"""
    fixed_files = 0
    total_fixes = 0
    
    print("🔍 O3 Pro Max - Step 1: Automated Syntax Cleanup")
    print("=" * 60)
    print(f"Scanning directory: {ROOT}")
    
    for py in ROOT.rglob("*.py"):
        try:
            # Skip backup files
            if '.bak' in str(py):
                continue
                
            txt = py.read_text(encoding='utf-8').splitlines(keepends=True)
            patched = []
            file_fixes = 0
            
            for line_num, line in enumerate(txt, 1):
                if pattern.match(line):
                    # Replace stray 'self.' with comment
                    patched.append("        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)\n")
                    print(f"  ✅ Fixed line {line_num}: {py.relative_to(ROOT)}")
                    file_fixes += 1
                    total_fixes += 1
                else:
                    patched.append(line)
            
            if file_fixes > 0:
                # Create backup
                backup_path = py.with_suffix('.py.bak')
                py.rename(backup_path)
                
                # Write fixed file
                py.write_text("".join(patched), encoding='utf-8')
                fixed_files += 1
                print(f"  📁 Fixed {file_fixes} issues in {py.relative_to(ROOT)}")
                
        except Exception as e:
            print(f"  ❌ Error processing {py}: {e}")
    
    print("=" * 60)
    print(f"✅ O3 Pro Max Step 1 Complete!")
    print(f"📊 Fixed {total_fixes} stray 'self.' statements in {fixed_files} files")
    print(f"💾 Backup files created with .bak extension")
    return fixed_files, total_fixes

def run_py_compile_test():
    """Test Python compilation after fixes"""
    print("\n🧪 Testing Python compilation...")
    
    error_count = 0
    test_files = list(ROOT.rglob("*.py"))
    
    for py in test_files[:10]:  # Test first 10 files as sample
        if '.bak' in str(py):
            continue
            
        try:
            compile(py.read_text(encoding='utf-8'), str(py), 'exec')
            print(f"  ✅ {py.relative_to(ROOT)}")
        except SyntaxError as e:
            print(f"  ❌ {py.relative_to(ROOT)}: {e}")
            error_count += 1
        except Exception as e:
            print(f"  ⚠️  {py.relative_to(ROOT)}: {e}")
    
    print(f"\n📊 Compilation test: {error_count} syntax errors in sample")
    return error_count

if __name__ == "__main__":
    print("🚀 Starting O3 Pro Max Optimization - Phase 1")
    
    # Step 1: Fix stray self. statements
    fixed_files, total_fixes = fix_stray_self_statements()
    
    # Step 2: Test compilation
    error_count = run_py_compile_test()
    
    print("\n" + "=" * 60)
    print("📋 O3 Pro Max Step 1 Summary:")
    print(f"  • Fixed files: {fixed_files}")
    print(f"  • Total fixes: {total_fixes}")
    print(f"  • Syntax errors remaining: {error_count} (in sample)")
    print("\n🎯 Next Step: Port-map sanitization (Step 3)")
    print("💡 Run: python3 o3_port_fix_script.py") 