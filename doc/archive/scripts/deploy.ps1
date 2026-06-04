# Frank Gemini Windows Deployment Script (PowerShell)

Write-Host "--- [1/3] Stopping and removing old container ---" -ForegroundColor Cyan
docker stop dream_frank_gemini 2>$null
docker rm dream_frank_gemini 2>$null

Write-Host "--- [2/3] Building new image ---" -ForegroundColor Cyan
docker build -t dream-frank:latest .

Write-Host "--- [3/3] Starting container with Beijing Time and Log mapping ---" -ForegroundColor Cyan
docker run -d `
  --name dream_frank_gemini `
  --restart unless-stopped `
  -e TZ=Asia/Shanghai `
  -e FEISHU_APP_ID=cli_aa89fecd95f8dcce `
  -e FEISHU_APP_SECRET=5LX6SnpoaC6JM5FVUdxhLc64ZRNJwSXn `
  -e FEISHU_CHAT_ID=oc_4e6b6a580ff7e8221da473791d116e42 `
  -e MINIMAX_API_KEY=sk-cp-yB0Vqxzhlo4o535OK7dFCAGCPY96iJu490RiIex2bymWMYIkdXvMEWJhGOmxNs19u9eeh5hW1EZo1o9oC5DIKkct7uxZNtPiMqh1OaLYK0pRBlKAL2xbEU4 `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/logs:/app/logs" `
  dream-frank:latest

Write-Host "--- Deployment Complete! ---" -ForegroundColor Green
Write-Host "You can view logs by running: docker logs -f dream_frank_gemini"
