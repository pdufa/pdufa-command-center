/** Active installation requirements are a projection of the immutable task
 * catalog. Retirement never renumbers task IDs or edits saved acceptance proof.
 */
export function isActiveInstallationTask(section:number, task:number, label:string):boolean{
 if(section===4||section===5)return false;
 if(/\braas\b|\bgem(?:\s+jr)?\b/i.test(label))return false;
 // Historical completeness-rating work is not an independent medical analysis
 // requirement. Source counts and missingness remain ordinary evidence facts.
 if(section===7&&task===46)return false;
 return true;
}
export function activeInstallationTasks(catalog:readonly (readonly string[])[]){
 return catalog.flatMap((tasks,section)=>tasks.flatMap((label,task)=>
  isActiveInstallationTask(section,task,label)?[{
   id:`${String(section+1).padStart(2,"0")}-${String(task+1).padStart(3,"0")}`,
   section,task,label
  }]:[]));
}
