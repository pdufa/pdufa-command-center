/** Stable hierarchical labels for actual TOOLS selection options. */
export function toolsOptionCode(level:number,index:number,total:number):string{
  if(!Number.isInteger(level)||level<1||!Number.isInteger(index)||index<0||
     !Number.isInteger(total)||total<1||index>=total||total>26)throw Error("TOOLS_OPTION_INDEX_INVALID");
  return level+String.fromCharCode(97+index)+"/"+total;
}
