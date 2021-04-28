method=$1
iv=$2
src=$3
dst=$4

methods=("encrypt" "decrypt")

# input validation
if [[ ! ${methods[@]} =~ $method ]]; then
    echo "[ERROR][crypto.sh] ${method} is not a valid method."
    exit 1
elif [[ ! $src =~ ^(/?[a-zA-Z0-9._-]+)+$ ]]; then
    echo "[ERROR][crypto.sh] ${src} is not a valid path."
    exit 1
elif [[ ! $dest =~ ^(/?[a-zA-Z0-9._-]+)+$ ]]; then
    echo "[ERROR][crypto.sh] ${dest} is not a valid path."
    exit 1
elif [[ ! -f $src ]]; then
    echo "[ERROR][crypto.sh] ${src} is not a file."
    exit 1
fi

if [[ -f $iv ]]; then
    iv=$(cat $iv)
fi

if [[ $method = "decrypt" ]]
then
    flag=' -d'
else
    flag=''
fi

openssl enc -aes-256-cbc $flag -K "$OPENSSL_KEY" -iv "$iv" -in "$src" -out "$dst"