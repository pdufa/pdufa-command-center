/** Visibility-only profiles for the two registry RESULTS-POSTING tables.
 * Same authoritative 38-input evidence and M percentages remain intact.
 * Results posting is NOT necessarily the date of an issuer's Phase 3 readout:
 * hidden secondary topics can be reopened without changing research records.
 */
import {TOOLS_RATING_GROUPS,type ToolsRatingGroupKey,type ToolsRatingIngredientKey} from "./tools-rating-groups";
export type PostingSheetKind="before"|"after";
export type PostingVisibleGroup={
  key:ToolsRatingGroupKey;name:string;
  ingredients:readonly {key:ToolsRatingIngredientKey;name:string}[];
};
const PRE:Readonly<Record<ToolsRatingGroupKey,readonly string[]>>={
  M:["VER","MOD","MISS","CRIT"],A:["ER","FDA"],
  B:[],C:["POP","ACCESS"],D:["CASH","MOM","CAT"],E:[]
};
const POST:Readonly<Record<ToolsRatingGroupKey,readonly string[]>>={
  M:["VER","MOD","MISS","CRIT"],A:["ER","FDA"],
  B:["CL","SAF","COMP"],C:["POP","REV"],
  D:["VAL","CASH","MOM","CAT"],E:["APP","READY","GRADE"]
};
export function visiblePostingRatingGroups(
  kind:PostingSheetKind,showAll=false
):PostingVisibleGroup[]{
  const profile=kind==="before"?PRE:POST;
  return TOOLS_RATING_GROUPS
    .filter(g=>showAll||profile[g.key].length>0)
    .map(group=>({
      key:group.key,name:group.name,
      ingredients:group.ingredients.filter(ingredient=>
        showAll||profile[group.key].includes(ingredient.key))
    }));
}
export function visiblePostingTestCount(kind:PostingSheetKind,showAll=false):number{
  return visiblePostingRatingGroups(kind,showAll).reduce((total,g)=>total+g.ingredients.length,0);
}
