import {redirect} from "next/navigation";

/** Legacy TOP/BOTTOM route retired; users should see only FOCUS. */
export default function RetiredTopBottomPage(){
 redirect("/focus");
}
