./get-ad.ps1
docker build -t netdox .
docker run -it --name netdox-container netdox