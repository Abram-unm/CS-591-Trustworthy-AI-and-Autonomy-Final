import argparse
import networkx
import random
import csv
import matplotlib.pyplot as plt
from pathlib import Path


# Function to turn networkx graph into KeymaeraX code
def keymaerafy( G, output_path ):
    # Program start
    keymaera = "Theorem \"ReservoirSafety\"\n  "

    keymaera += "ProgramVariables.\n    "
    keymaera += "Real node;\n    "
    keymaera += "Real weight;\n  "
    keymaera += "End.\n\n  "

    keymaera += "Problem\n    "
    keymaera += "(\n      "
    keymaera += "node = 0 & weight = 0\n    "
    keymaera += ")\n    "
    keymaera += "->\n    "
    keymaera += "[\n      "
    keymaera += "(\n        "

    # Each node block
    for i, node in enumerate( G.nodes( ) ):
        keymaera += "(\n          "
        
        keymaera += f"?node = {node};\n          "
        keymaera += "(\n            "

        # Each transition from node to node
        successorNodes = list( G.successors( node ) )
        for j, nextNode in enumerate( successorNodes ):
            edge_weight = G[node][nextNode]["weight"]
            keymaera += f"node := {nextNode}; weight := weight + {edge_weight}\n          "
            if j < len( successorNodes ) - 1:
                keymaera += "  ++\n            "

        keymaera += ")\n        "

        keymaera += ")\n      "

        if i < len( G.nodes( ) ) - 1:
            keymaera += "  ++\n        "
    
    keymaera += ")*\n    "

    keymaera += "]\n  "
    keymaera += "(weight >= 0)\n  "
    keymaera += "End.\n"
    keymaera += "End.\n"

    # Write to file
    with open( output_path, "w") as keymaeraXFile:
        keymaeraXFile.write( keymaera )


def positive_int( value ):
    node_count = int( value )
    if node_count < 1:
        raise argparse.ArgumentTypeError( "node count must be at least 1" )
    return node_count


def main():
    parser = argparse.ArgumentParser( description = "Generate a random weighted graph." )
    parser.add_argument(
        "--node-count",
        type = positive_int,
        help = "number of nodes (defaults to a random count from 3 to 10)",
    )
    parser.add_argument(
        "--output-name",
        default = "graph",
        help = "output filename stem for the CSV, PNG, and KeymaeraX files",
    )
    args = parser.parse_args()

    if not args.output_name or Path( args.output_name ).name != args.output_name:
        parser.error( "output name must be a non-empty filename stem, not a path" )

    random.seed( 2 )
    node_count = args.node_count or random.randint( 3, 10 )

    # Generate a connected Gn,p graph (an Erdos-Renyi graph) with p = 0.6.
    G = networkx.gnp_random_graph( node_count, 0.6 )
    while not networkx.is_connected( G ):
        G = networkx.gnp_random_graph( node_count, 0.6 )

    # Give weights to each edge
    for ( source, dest ) in G.edges( ):
        G.edges[source, dest]['weight'] = random.randint( 0, 100 ) / 100

    # Make graph directed for KeymaeraX
    G = G.to_directed( )

    # Put data in CSV for use in other applications
    connections = []
    for ( source, dest ) in G.edges( ):
        connections.append( {
            "source": source,
            "dest": dest,
            "weight": G.edges[source, dest]["weight"],
            "max_flow_rate": "",
        } )

    # Write related outputs using the requested name.
    csv_path = Path( "data" ) / f"{args.output_name}.csv"
    image_path = Path( "data" ) / f"{args.output_name}.png"
    keymaera_path = Path( "keymaera" ) / f"{args.output_name}.kyx"
    with open( csv_path, "w", newline="" ) as csvfile:
        fieldnames = ["source", "dest", "weight", "max_flow_rate"]
        writer = csv.DictWriter( csvfile, fieldnames = fieldnames )
        writer.writeheader()
        writer.writerows( connections )

    keymaerafy( G, keymaera_path )

    # Draw nodes and edges
    pos = networkx.spring_layout( G )
    networkx.draw( G, pos )

    # Add edge weights
    networkx.draw_networkx_edge_labels( G, pos, edge_labels = networkx.get_edge_attributes( G, "weight" ) )

    plt.savefig( image_path )
    plt.close( )


if __name__ == "__main__":
    main()
