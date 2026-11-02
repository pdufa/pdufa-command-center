/** One canonical M–E visual taxonomy shared by TOOLS and both Phase 3 registry tables.
 * These are research-audit headings; the presence of a column is not a grade. */
export const TOOLS_RATING_GROUPS=[
 {key:"M",name:"Missing",ingredients:[{key:"VER",name:"Verified inputs"},{key:"MOD",name:"Modeled inputs"},{key:"MISS",name:"Missing inputs"},{key:"CRIT",name:"Critical gaps"}]},
 {key:"A",name:"Evidence",ingredients:[{key:"ER",name:"Evidence readiness"},{key:"FDA",name:"Regulatory readiness"}]},
 {key:"B",name:"Medical",ingredients:[{key:"CL",name:"Clinical benefit"},{key:"SAF",name:"Safety"},{key:"COMP",name:"Competitive advantage"}]},
 {key:"C",name:"Commercial",ingredients:[{key:"POP",name:"Patient opportunity"},{key:"ACCESS",name:"Commercial access"},{key:"REV",name:"Revenue potential"}]},
 {key:"D",name:"Stock",ingredients:[{key:"VAL",name:"Valuation opportunity"},{key:"CASH",name:"Financial strength"},{key:"MOM",name:"Stock momentum"},{key:"FLOW",name:"Ownership and trading"},{key:"CAT",name:"Catalyst setup"}]},
 {key:"E",name:"Final",ingredients:[{key:"APP",name:"Appreciation opportunity"},{key:"READY",name:"Research readiness"},{key:"GRADE",name:"Opportunity grade"}]}
] as const;
export type ToolsRatingGroupKey=typeof TOOLS_RATING_GROUPS[number]["key"];
export type ToolsRatingIngredientKey=typeof TOOLS_RATING_GROUPS[number]["ingredients"][number]["key"];
