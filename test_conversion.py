#!/usr/bin/env python3
"""
문서 변환 기능 테스트 스크립트
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 변환 함수 임포트
# 파일명에 특수문자가 있어서 직접 임포트
import importlib.util
spec = importlib.util.spec_from_file_location("converter", "/Users/choichunsung/Documents/GitHub/myproduct_v4/youtubedownloading/유트브다운로더&미디어변환기_v2.py")
converter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter_module)
convert_document = converter_module.convert_document

def test_log(message):
    print(f"[LOG] {message}")

def test_conversion():
    # 테스트 파일들
    test_files = [
        ("/Users/choichunsung/Documents/GitHub/myproduct_v4/youtubedownloading/test_document_with_table.docx", "md", "DOCX → MD"),
        ("/Users/choichunsung/Documents/GitHub/myproduct_v4/youtubedownloading/test_presentation.pptx", "md", "PPTX → MD")
    ]
    
    for input_file, output_format, test_name in test_files:
        print("=" * 60)
        print(f"{test_name} 변환 테스트")
        print("=" * 60)
        
        if not os.path.exists(input_file):
            print(f"ERROR: 입력 파일을 찾을 수 없습니다: {input_file}")
            continue
        
        print(f"입력 파일: {input_file}")
        print(f"출력 형식: {output_format}")
        print()
        
        try:
            success, result = convert_document(input_file, output_format, test_log)
            
            if success:
                print(f"✅ 변환 성공: {result}")
                
                # 결과 파일 내용 확인
                if os.path.exists(result):
                    print("\n" + "=" * 50)
                    print("변환된 MD 파일 내용:")
                    print("=" * 50)
                    with open(result, 'r', encoding='utf-8') as f:
                        content = f.read()
                        print(content[:1500])  # 첫 1500자만 출력
                        if len(content) > 1500:
                            print("\n... (내용이 더 있습니다)")
                else:
                    print(f"⚠️  결과 파일을 찾을 수 없습니다: {result}")
            else:
                print(f"❌ 변환 실패: {result}")
                
        except Exception as e:
            print(f"❌ 변환 중 오류 발생: {str(e)}")
        
        print("\n")

if __name__ == "__main__":
    test_conversion()