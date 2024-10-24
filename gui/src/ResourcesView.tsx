import { useState, useEffect } from "react";
import "./ResourcesView.css";
import { DataGrid, GridRowsProp, GridColDef } from "@mui/x-data-grid";
import type {} from "@mui/x-data-grid/themeAugmentation";

const default_rows: GridRowsProp = [
  {
    first_seen: null,
    last_seen: null,
    modules: ["http"],
    resource: "https://example.com/",
    id: "Loading",
    source: null,
  },
];

const columns: GridColDef[] = [
  { field: "id", headerName: "id"},
  { field: "resource", headerName: "resource"},
  { field: "modules", headerName: "modules"},
  { field: "source", headerName: "source"},
  { field: "first_seen", headerName: "first_seen"},
  { field: "last_seen", headerName: "last_seen"},
];

interface Resource
{
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
  const json = await response.json();
  console.log(json);
  const data = [
    {
      first_seen: null,
      last_seen: null,
      modules: ["http"],
      resource: "https://example.com/",
      id: null,
      source: null,
    },
    {
      first_seen: null,
      last_seen: null,
      modules: ["http"],
      resource: "https://example.com/",
      id: null,
      source: null,
    },
  ];
  fix_ids(data);

  return data;
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
      <div style={{ height: 300, width: "100%" }}>
        <DataGrid rows={rows} columns={columns} />
      </div>
    </>
  );
}

export default ResourcesView;
