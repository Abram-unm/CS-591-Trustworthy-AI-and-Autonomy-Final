import networkx
import random
import csv
import matplotlib.pyplot as plt


# Function to turn networkx graph into KeymaeraX code
def keymaerafy( G ):
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
            keymaera += f"node := {nextNode}; weight := weight + {edge_weight}\n            "
            if j < len( successorNodes ) - 1:
                keymaera += "++\n            "

        keymaera += ")\n          "

        keymaera += ")\n      "

        if i < len( G.nodes( ) ) - 1:
            keymaera += "  ++\n      "
    
    keymaera += ")*\n    "

    keymaera += "]\n  "
    keymaera += "(weight >= 0)\n  "
    keymaera += "End.\n"
    keymaera += "End.\n"

    # Write to file
    with open( "keymaera/graph.kyx", "w") as keymaeraXFile:
        keymaeraXFile.write( keymaera )


# Choose random node count in range
node_count = random.randint( 3, 10 )

# Graph for n nodes, each edge with p chance to exist
# Returns a Gn,p random graph, also known as an Erdos-Renyi graph or a binomial graph.
# Choose 60% chance for each edge to exist, can easily tweak
G = networkx.gnp_random_graph( node_count, 0.6 )

# Make sure graph is connected
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
    connections.append( {"source": source, "dest": dest, "weight": G.edges[source, dest]["weight"]} )

# write to csv
with open( "data/graph.csv", "w", newline="" ) as csvfile:
    fieldnames = ["source", "dest", "weight"]
    writer = csv.DictWriter( csvfile, fieldnames = fieldnames )

    writer.writeheader( )
    writer.writerows( connections )

# Turn graph into KeymaeraX format
keymaerafy( G )


# Draw nodes and edges
pos = networkx.spring_layout( G )
networkx.draw( G, pos )

# Add edge weights
networkx.draw_networkx_edge_labels( G, pos, edge_labels = networkx.get_edge_attributes( G, "weight" ) )

plt.savefig( "data/graph.png" )

plt.close( )
