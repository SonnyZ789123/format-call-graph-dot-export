set -e

rawGraphPath="$1"
outputFileName="$2"
nodeCoveragePath="$3"
edgeCoveragePath="$4"
scoresPath="$5"

if [ -z "$rawGraphPath" ] || [ -z "$outputFileName" ] || [ -z "$nodeCoveragePath" ] || [ -z "$edgeCoveragePath" ]; then
  echo "Usage: $0 <raw_graph_path> <output_file_name> <node_coverage_path> <edge_coverage_path> [graph_ranking_path]"
  exit 1
fi

python3 main.py $rawGraphPath $outputFileName $nodeCoveragePath $edgeCoveragePath $scoresPath

dot -Tsvg out/"$outputFileName".dot -o out/"$outputFileName".svg

open out/"$outputFileName".svg