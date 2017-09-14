# bash 3 does not support associative arrays, which is needed on Big Iron.
# So employ these hacks.
hput () {
    eval hash`echo "$1" |sed -e 's/[^a-zA-Z0-9]/_/g'`='"$2"'
}

hget () {
    eval echo '"${hash'`echo "$1" | sed -e 's/[^a-zA-Z0-9]/_/g'`'#hash}"'
}

ALL_FILES=()

rm -f chkperms.log
rm -f unspeced_files.log

ERR=0

# First we build a comprehensive set of files that expand wildcards from chkperms.txt
#
# NOTE: dirname* will only expand to 'dirname', unlike 'cp -a' for ex. If you want to
# include subdirectories, you must use the dirname/* syntax. You may include other levels
# as well such as dirname/*/*. However there's no way to specify infinite recursion.
while read -r line || [[ -n "$line" ]]; do
    set -f
    IFS=':'
    i=0
    TOKENARR=()
    for token in $line; do
        # bash3 doesn't support += with arrays
        TOKENARR[${#TOKENARR[@]}]=$token
    done

    if [ ${#TOKENARR[@]} -ne 2 ]; then
        echo "syntax error on line $line"
        exit 1
    fi

    fileset="${TOKENARR[0]}"
    chkperms=${TOKENARR[1]}

    IFS=$' \t\n'
    set +f
    FINDOUT=( $(ls -d -1 $fileset 2>/dev/null) )
    finderr=$?
    set -f

    if [ $finderr -eq 0 ]; then
        for file in "${FINDOUT[@]}"; do
            tmpline="${file}:$chkperms"
            ALL_FILES[${#ALL_FILES[@]}]=$tmpline
        done
    fi
done < "chkperms.txt"

# Now stat each file generated from the step above and check for permissions
for entry in "${ALL_FILES[@]}"; do
    IFS=':'
    TOKENARR=()
    for token in $entry; do
        TOKENARR[${#TOKENARR[@]}]=$token
    done
    if [ ${#TOKENARR[@]} -ne 2 ]; then
        echo "syntax error on file $entry"
        exit 1
    fi
    filename=${TOKENARR[0]}
    chkperms=${TOKENARR[1]}
    if [[ -f $filename || -d $filename ]]; then
        # *sigh* even 'stat' doesn't exist on Big Iron
        cmd="perl -le '@pv=stat(\"$filename\"); printf \"%03o\", \$pv[2] & 0777;'"
        fileperms=$(eval $cmd)
        IFS=','
        PERMARR=($chkperms)
        found="false"
        for permentry in "${PERMARR[@]}"; do
            if [ "$permentry" == "$fileperms" ]; then
                found="true"
            fi
        done
        if [ "$found" == "false" ]; then
            echo "Bad permissions found on $filename (expected=$chkperms found=$fileperms)" |tee -a chkperms.log
            ERR=1
        fi
        # add to hash to compare with total set of files
        hput $filename true
    fi
done

# Here's a sanity check that the full set of files in /act and /opt/act is not a
# superset of the files we generated beforehand in chkperms.txt. This is to ensure
# we didn't miss anything. Write the results out to unspeced_files.txt.
IFS=$' \t\n'
set +f
FINDREAL=( $(find /act) )

for file in "${FINDREAL[@]}"; do
    out=$(hget $file)
    if [ -z $out ]; then
        echo "File $file not found in spec" |tee -a unspeced_files.log
        ERR=1
    fi
done

FINDREAL=( $(find /opt/act ) )
for file in "${FINDREAL[@]}"; do
    out=$(hget $file)
    if [ -z $out ]; then
        echo "File $file not found in spec" |tee -a unspeced_files.log
        ERR=1
    fi
done


exit $ERR
