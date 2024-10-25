import { useState, useEffect } from "react";
import "./ResourcesView.css";
import { DataGrid, GridRowsProp, GridColDef } from "@mui/x-data-grid";
import type {} from "@mui/x-data-grid/themeAugmentation";

const default_rows: GridRowsProp = [
  {
    first_seen: null,
    last_seen: null,
    modules: ["Loading..."],
    resource: "Loading...",
    id: "Loading...",
    source: null,
  },
];

const columns: GridColDef[] = [
  { field: "id", headerName: "id", width: 80 },
  { field: "resource", headerName: "resource", width: 200 },
  { field: "modules", headerName: "modules", width: 200 },
  { field: "source", headerName: "source", width: 200 },
  { field: "first_seen", headerName: "first_seen", width: 300 },
  { field: "last_seen", headerName: "last_seen", width: 300 },
];

interface Resource {
  first_seen: string | null;
  last_seen: string | null;
  modules: string[];
  resource: string;
  id: number | string | null;
  source: string | null;
}

function fix_ids(data: Resource[]) {
  let counter = -1;
  for (const x of data) {
    if (x.id === undefined || x.id === null) {
      x.id = counter--;
    }
  }
}

async function fetch_table_data() {
  const response = await fetch("/api/resources");
  const resources: Resource[] = await response.json();
  console.log(resources);
  fix_ids(resources);
  return resources;
}

function ResourcesView() {
  const [rows, setRows] = useState(default_rows);
  // setRows(fetch_table_data());
  useEffect(() => {
    fetch_table_data().then((data) => setRows(data));
  }, []);
  return (
    <>
      <h1>Resources</h1>
      <div style={{ height: "70vh", width: "100%" }}>
        <DataGrid rows={rows} columns={columns} />
      </div>
    </>
  );
}

export default ResourcesView;
