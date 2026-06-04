@echo off
echo --- [1/3] Stopping and removing old container ---
docker stop dream_frank_gemini 2>nul
docker rm dream_frank_gemini 2>nul

echo --- [2/3] Building new image ---
docker build -t dream-frank:latest .

echo --- [3/3] Starting container with Beijing Time and Log mapping ---
docker run -d ^
  --name dream_frank_gemini ^
  --restart unless-stopped ^
  -e TZ=Asia/Shanghai ^
  -e FEISHU_APP_ID=cli_aa89fecd95f8dcce ^
  -e FEISHU_APP_SECRET=5LX6SnpoaC6JM5FVUdxhLc64ZRNJwSXn ^
  -e FEISHU_CHAT_ID=oc_4e6b6a580ff7e8221da473791d116e42 ^
  -e MINIMAX_API_KEY=sk-cp-yB0Vqxzhlo4o535OK7dFCAGCPY96iJu490RiIex2bymWMYIkdXvMEWJhGOmxNs19u9eeh5hW1EZo1o9oC5DIKkct7uxZNtPiMqh1OaLYK0pRBlKAL2xbEU4 ^
  -v "%cd%/data:/app/data" ^
  -v "%cd%/logs:/app/logs" ^
  dream-frank:latest

echo --- Deployment Complete! ---
pause
