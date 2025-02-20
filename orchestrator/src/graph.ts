export const allPreprocessors: (string | number)[][] = [
  ["PreA", 1.0, JSON.stringify([]), JSON.stringify([])],
  ["PreB", 1.1, JSON.stringify(["PreA"]), JSON.stringify([])],
  ["PreC", 2.0, JSON.stringify(["PreA"]), JSON.stringify([])],
  ["PreD", 1.2, JSON.stringify(["PreB"]), JSON.stringify([])],
  ["PreE", 3.0, JSON.stringify(["PreB"]), JSON.stringify([])],
  ["PreH", 3.0, JSON.stringify(["PreE"]), JSON.stringify([])],
  ["PreF", 3.0, JSON.stringify(["PreC"]), JSON.stringify([])],
  ["PreG", 3.0, JSON.stringify(["PreC"]), JSON.stringify([])],
  ["PreI", 3.0, JSON.stringify(["PreF"]), JSON.stringify([])]
];

//returns the optional preprocessors required for the given preprocessor
export function getOptionalPreprocessors(preprocessor: (string | number)[]): (string | number)[][] {
    const optionalNames = JSON.parse(preprocessor[3] as string); // Convert back to an array
    if(optionalNames.length != 0){
        return allPreprocessors.filter(p => optionalNames.includes(p[0] as string)); // Find full preprocessors
    } else {
        return [];
    }
}

//returns the required preprocessors required for the given preprocessor
export function getRequiredPreprocessors(preprocessor: (string | number)[]): (string | number)[][] {
    const requiredNames = JSON.parse(preprocessor[2] as string); // Convert back to an array
    if(requiredNames.length != 0){
        return allPreprocessors.filter(p => requiredNames.includes(p[0] as string)); // Find full preprocessors
    } else {
        return [];
    }
}

class Graph {
    nodes: Map<string, GraphNode>;
  
    constructor() {
      this.nodes = new Map();
    }
  
    addNode(preprocessors: (string | number)[]): GraphNode {
      const name = preprocessors[0] as string; 
      if (!this.nodes.has(name)) {
        const newNode = new GraphNode(preprocessors);
        this.nodes.set(name, newNode);
      }
      return this.nodes.get(name)!;
    }

    constructGraph(P: (string | number)[][], H: (string | number)[][]) : Set<GraphNode>  {
      const R = new Set<GraphNode>();
      const combinedArray = P.concat(H);

      const Pset = new Set<string>();
      for(const preprocessor of P){
        Pset.add(preprocessor[0] as string);
      }
      
      for (const preprocessor of combinedArray) {
        const requiredPreprocessors = getRequiredPreprocessors(preprocessor);
        const optionalPreprocessors = getOptionalPreprocessors(preprocessor);

        if(requiredPreprocessors.every((r) => Pset.has(r[0] as string))){
          const node = this.addNode(preprocessor);
          const tmp = optionalPreprocessors.filter((o) => Array.isArray(o) && Pset.has(o[0] as string));

          if (requiredPreprocessors.length === 0 && tmp.length === 0) {
            R.add(node);
          } else {
            for(const reqPrep of requiredPreprocessors){
              const nodePrime = this.addNode(reqPrep);
              node.parents.add(nodePrime);
              nodePrime.children.add(node);
            }

            for(const optPrep of optionalPreprocessors){
              const nodePrime = this.addNode(optPrep);
              node.parents.add(nodePrime);
              nodePrime.children.add(node);
            }
          }
        }   
      }
      
      return R;
  }

    //Uses Kahn's algorithm to check if the graph contains any cycles 
    //If the number of processed nodes != number of total nodes, a cycle exists
    isAcyclic(): boolean {
      const inDegreeMap = new Map<GraphNode, number>();  //number of parents the node has 
      const noParentQueue: GraphNode[] = [];      //nodes with 0 parents (indegree = 0)
      let processedCount = 0;                         //nodes processed so far

      //set the inDegree map for each node (key) with number of parents it has (value)
      for (const node of this.nodes.values()) {
          inDegreeMap.set(node, node.parents.size);    
        if (node.parents.size === 0) {
          noParentQueue.push(node);   //add nodes with 0 parents to queue
        }
      }

      //process queue until empty 
      while (noParentQueue.length > 0) {
        const currentNode = noParentQueue.shift()!;
        processedCount++;

        //for each child of the node, decrease its parent number in the map by 1
        for (const child of currentNode.children) {
          const childInDegree = inDegreeMap.get(child)! - 1;
          inDegreeMap.set(child, childInDegree);

          //if it has no parents left, push to queue 
          if (childInDegree === 0) {
              noParentQueue.push(child);
          }
        }
      }
      //should be false if cycle exists
      return processedCount === this.nodes.size;  
    }
}
  
class GraphNode {
    preprocessor: (string | number)[];    //preprocessor that this node represents
    parents: Set<GraphNode>;
    children: Set<GraphNode>;
    
    constructor(preprocessors: (string | number)[]) {
      this.preprocessor = preprocessors;
      this.parents = new Set();
      this.children = new Set();
    }
  
    get name(): string {
      return this.preprocessor[0] as string;
    }
}
  
function main() {
    console.log("---------Building Dependency Graph---------")
    const graph = new Graph();
    const readyNodes = graph.constructGraph(allPreprocessors, []);
    const isAcyclic = graph.isAcyclic();
   
    if(!isAcyclic){
      console.error("Error: Preprocessor Dependency graph contains cycle.")
    }
    else {
      printGraph(graph);
      executePreprocessorsFromGraph(graph, readyNodes);
    }
}

function printGraph(graph: Graph) {
    console.log("\n=== Graph Structure ===");

    for (const node of graph.nodes.values()) {
        console.log(`\nNode: ${node.name}`);
        
        if (node.parents.size > 0) {
            console.log(`  ⬆ Parents: ${Array.from(node.parents).map(n => n.name).join(", ")}`);
        } else {
            console.log("  ⬆ Parents: None");
        }

        if (node.children.size > 0) {
            console.log(`  ⬇ Children: ${Array.from(node.children).map(n => n.name).join(", ")}`);
        } else {
            console.log("  ⬇ Children: None");
        }
    }
}

//This will be the general way we execute preprocessors, should work for both series and parallel
function executePreprocessorsFromGraph(G: Graph, R: Set<GraphNode>){
  const prepQueue = Array.from(R);    //queue of preprocessors 
  while(prepQueue.length > 0){
      //--HERE IS WHERE WE WILL DEQUEUE ALL PREPROCESSORS AT ONCE AND RUN THEM IN PARALLEL
      const preprocessor = prepQueue.shift() as GraphNode;
      //run the preprocessor here
      const preprocessorName = preprocessor.preprocessor[0];
      console.log(`RUNNING PREPROCESSOR: ${preprocessorName}`);

      //response check goes here 
      
      //for each child of that preprocessor remove it as a parent from that child 
      //(disown child)
      for(const child of preprocessor.children){
          child.parents.delete(preprocessor);
          if(child.parents.size == 0){
              prepQueue.push(child);
          }
      }
      console.log();
  }
  
}
main();
