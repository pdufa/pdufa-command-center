import {redirect} from "next/navigation";

/** The old 762-trial scoring cohort is no longer an active spreadsheet. */
export default function RetiredRaas762Page(){
 redirect("/p3-post-data");
}
