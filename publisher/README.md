# Master 서명 요청과 자동 배포

`current-request.json`은 도우미의 현재 요청이다. 검증된 후보를 Master가 승인·서명·전달하면 GitHub Actions가 운영 서명·파일·Windows 업데이트/복구를 검사하고 온라인 목록을 자동 게시한다. 대화에 완료 메시지를 입력할 필요가 없다.

[절차·상태·실패 복구](automation/README.md). 요청 등록만으로 자동 서명하지 않으며 개인키는 Master PC에 유지한다. 도우미 전달 완료와 게시 완료, 실제 사용자 PC 적용을 구분한다.
