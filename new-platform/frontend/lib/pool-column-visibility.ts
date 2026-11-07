/** Independent column-group visibility for the POOL Master spreadsheet. */
export type ColumnLayout<K extends string>={
 expanded:string[];hiddenSegments:string[];hiddenColumns:K[];
};
export function isGroupVisible<K extends string>(
 layout:ColumnLayout<K>,group:readonly string[],
 columns:Readonly<Record<string,readonly K[]>>
):boolean{
 return group.some(id=>layout.expanded.includes(id)
  && !layout.hiddenSegments.includes(id)
  && (columns[id]||[]).some(k=>!layout.hiddenColumns.includes(k)));
}
export function toggleColumnGroup<K extends string>(
 layout:ColumnLayout<K>,group:readonly string[],
 columns:Readonly<Record<string,readonly K[]>>
):ColumnLayout<K>{
 if(isGroupVisible(layout,group,columns)){
  return {...layout,hiddenSegments:[...new Set([...layout.hiddenSegments,...group])]};
 }
 const belongs=new Set(group.flatMap(id=>columns[id]||[]));
 return {
  expanded:[...new Set([...layout.expanded,...group])],
  hiddenSegments:layout.hiddenSegments.filter(id=>!group.includes(id)),
  hiddenColumns:layout.hiddenColumns.filter(k=>!belongs.has(k))
 };
}
