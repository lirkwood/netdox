cd /opt/app/netdox
python3 generate.py

cd /opt/app/linktest
python3 linktools.py

cd /opt/app
zip -q -r psml.zip /opt/app/out

echo "Done :)"