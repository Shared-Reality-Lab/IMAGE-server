import { getOptional, getRequired } from "./docker";
import Docker from "dockerode";

export const docker = new Docker();
export class Graph {
    nodes: Map<string, GraphNode>;
  
    constructor() {
      this.nodes = new Map();
    }
  
    addNode(service : (string | number)[], isPreprocessor: boolean): GraphNode {
      const name = service[0] as string; 
      if (!this.nodes.has(name)) {
        const newNode = new GraphNode(service);
        if(isPreprocessor){
          newNode.type = "P"; //type P corresponds to preprocessor services
        } else {
          newNode.type = "H"; //type H corresponds to preprocessor services
        }
        this.nodes.set(name, newNode);
      }
      return this.nodes.get(name)!;
    }

    async constructGraph(P: (string | number)[][], H: (string | number)[][], containers: Docker.ContainerInfo[]) : Promise<Set<GraphNode>>  {
      const R = new Set<GraphNode>();
      const combinedArray = P.concat(H);

      const Pset = new Set<string>();
      for(const preprocessor of P){
        Pset.add(preprocessor[0] as string);
      }
      
      for (const service of combinedArray) {
        const requiredServices = getRequired(containers, service[0] as string, combinedArray);
        let optionalPreprocessors = [] as (string | number)[][];
        //Only get the optional preprocessors if its a preprocessor
        optionalPreprocessors = getOptional(containers, service[0] as string, combinedArray);
        

        if(optionalPreprocessors && requiredServices && requiredServices.every((r) => Pset.has(r[0] as string))){
          const node = this.addNode(service, P.some(p => p[0] == service[0]));
          const tmp = optionalPreprocessors.filter((o) => Array.isArray(o) && Pset.has(o[0] as string));

          //If the preprocessor has no required or optional dependencies
          //then we can add it to the queue of ready to run preprocessors 
          if (requiredServices.length === 0 && tmp.length === 0) {
            R.add(node);
          } else {
            for(const reqPrep of requiredServices){
              //pass the preprocessor & true if its a preprocessor by checking if its a part of the preprocessors array 
              const nodePrime = this.addNode(reqPrep, P.some(p => p[0] == reqPrep[0])); 
              node.parents.add(nodePrime);
              nodePrime.children.add(node);
            }

            for(const optPrep of tmp){
              const nodePrime = this.addNode(optPrep, P.some(p => p[0] == optPrep[0]));
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
  
export class GraphNode {
    value: (string | number)[];    //preprocessor that this node represents
    parents: Set<GraphNode>;
    children: Set<GraphNode>;
    type: string;

    constructor(preprocessors: (string | number)[]) {
      this.value = preprocessors;
      this.parents = new Set();
      this.children = new Set();
      this.type = "";
    }
  
    get name(): string {
      return this.value[0] as string;
    }
}
  

export function printGraph(graph: Graph) {
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


