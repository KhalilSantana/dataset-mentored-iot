#! /bin/bash
pushd /app/scripts/server-analysis
mkdir .tmp_exp_analyzer

# if not two args
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <experiment_file> <experiment_duration>"
    exit 1
fi

# If file not exist
if [ ! -f pcap_to_csv ]; then
    
    echo "Compiling pcap_to_csv..."
    make
fi

EXPFILE=$1
EXPERIMENT_DURATION=$2
echo "Extracting $EXPFILE..."
tar -zxf $EXPFILE -C .tmp_exp_analyzer --wildcards '*server*' # TODO: UNCOMMENT THIS

tar -zxf $EXPFILE -C .tmp_exp_analyzer --wildcards '*MENTORED_READY.txt'

START_TIMESTAMP=$(cat .tmp_exp_analyzer/*MENTORED_READY.txt)
rm .tmp_exp_analyzer/*MENTORED_READY.txt

echo "Extracted $EXPFILE"

echo "Running experiment analyzer..."
cd .tmp_exp_analyzer
for f in */*.tar; do mkdir ${f}.files; tar -xf "$f" -C ${f}.files; done

# Find recursevely all .pcap files and iterate over them
for f in $(find . -name "*.pcapng"); do
    echo "Converting $f to csv..."
    # tshark -r $f -T fields -e frame.time_epoch -e frame.len -e ip.src -e ip.dst -e tcp.srcport -e tcp.dstport -e tcp.seq -e tcp.ack -e tcp.flags -e tcp.window_size -e tcp.analysis.ack_rtt -e tcp.analysis.ack_rtt -e tcp.analysis.bytes_in_flight
    ../pcap_to_csv $f packets.csv # TODO UNCOMMENT THIS
    set -x
    python3 ../analyze_output_pcap.py -s 22 -f packets.csv -t $EXPERIMENT_DURATION -u $START_TIMESTAMP
done

cd ..
echo "Experiment analyzer finished"
rm -rf .tmp_exp_analyzer
popd