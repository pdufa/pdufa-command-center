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


/** Explicit SHOW/HIDE controls are scoped to one POOL section. A section SHOW
 * restores all its columns; HIDE retains each column preference for review. */
export function setPoolSegmentVisibility<K extends string>(
 layout:ColumnLayout<K>,segment:string,
 columns:Readonly<Record<string,readonly K[]>>,show:boolean
):ColumnLayout<K>{
 if(!columns[segment])return layout;
 if(!show)return {...layout,hiddenSegments:[...new Set([...layout.hiddenSegments,segment])]};
 const keys=new Set(columns[segment]);
 return {...layout,
  expanded:[...new Set([...layout.expanded,segment])],
  hiddenSegments:layout.hiddenSegments.filter(id=>id!==segment),
  hiddenColumns:layout.hiddenColumns.filter(key=>!keys.has(key))
 };
}

/** An item SHOW can restore its parent without changing any other segment. */
export function setPoolColumnVisibility<K extends string>(
 layout:ColumnLayout<K>,segment:string,key:K,
 columns:Readonly<Record<string,readonly K[]>>,show:boolean
):ColumnLayout<K>{
 if(!(columns[segment]||[]).includes(key))return layout;
 return {...layout,
  expanded:show?[...new Set([...layout.expanded,segment])]:layout.expanded,
  hiddenSegments:show?layout.hiddenSegments.filter(id=>id!==segment):layout.hiddenSegments,
  hiddenColumns:show?layout.hiddenColumns.filter(item=>item!==key)
    :[...new Set([...layout.hiddenColumns,key])]
 };
}
