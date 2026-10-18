import networkx
import random
import csv


# Choose random node count in range
node_count = random.randint( 3, 10 )

# Graph for n nodes, each edge with p chance to exist
# Returns a Gn,p random graph, also known as an Erdos-Renyi graph or a binomial graph.
# Choose 80% chance for each edge to exist, can easily tweak
G = networkx.gnp_random_graph( node_count, 0.8 )

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
