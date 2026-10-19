import networkx
import random
import csv
import matplotlib.pyplot as plt


# Choose random node count in range
node_count = random.randint( 3, 10 )

# Graph for n nodes, each edge with p chance to exist
# Returns a Gn,p random graph, also known as an Erdos-Renyi graph or a binomial graph.
# Choose 60% chance for each edge to exist, can easily tweak
G = networkx.gnp_random_graph( node_count, 0.6 )

# Give weights to each edge
for ( source, dest ) in G.edges( ):
    G.edges[source, dest]['weight'] = random.randint( 0, 100 ) / 100

# Put data in CSV for use in other applications
connections = []

for ( source, dest ) in G.edges( ):
    connections.append( {"source": source, "dest": dest, "weight": G.edges[source, dest]["weight"]} )


with open( "data/graph.csv", "w", newline="" ) as csvfile:
    fieldnames = ["source", "dest", "weight"]
    writer = csv.DictWriter( csvfile, fieldnames = fieldnames )

    writer.writeheader( )
    writer.writerows( connections )


# Draw nodes and edges
pos = networkx.spring_layout( G )
networkx.draw( G, pos )

# Add edge weights
networkx.draw_networkx_edge_labels( G, pos, edge_labels = networkx.get_edge_attributes( G, "weight" ) )

plt.savefig( "data/graph.png" )

plt.close( )
