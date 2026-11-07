import {redirect} from "next/navigation";

/** Legacy TOP/BOTTOM route retired; users should see only P3 Post-Data. */
export default function RetiredTopBottomPage(){
 redirect("/p3-post-data");
}
