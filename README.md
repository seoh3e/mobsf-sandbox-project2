# MobSF Sandbox Project

## 개요

MobSF API를 활용해 **Android APK 정적 분석을 자동화**하는 프로젝트이다.
GUI 없이 스크립트 기반으로 분석 결과를 저장·공유하는 것을 목표로 한다.

## 기능

* APK 정적 분석 자동화 (MobSF API)
* JSON 분석 리포트 저장

## 구조

```text
scripts/   # 분석 스크립트
samples/   # APK 샘플
outputs/   # 분석 결과
```

## 진행 현황

* 정적 분석 자동화 완료
* 암호화 DEX / 동적 로딩 미확인
* Native 라이브러리(.so) 포함 APK 확인