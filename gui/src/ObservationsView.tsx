import { useState, useEffect } from "react";
import "./ObservationsView.css";
import { DataGrid, GridRowsProp, GridColDef } from "@mui/x-data-grid";
import type {} from "@mui/x-data-grid/themeAugmentation";

const default_rows: GridRowsProp = [
  {
    id: "Loading...",
    resource: "Loading...",
    module: "Loading...",
    attribute: null,
    value: null,
    first_seen: null,
    last_changed: null,
    last_seen: null,
  },
];

const columns: GridColDef[] = [
  { field: "id", headerName: "id", width: 80 },
  { field: "resource", headerName: "resource", width: 200 },
  { field: "module", headerName: "module", width: 100 },
  { field: "attribute", headerName: "attribute", width: 200 },
  { field: "value", headerName: "value", width: 200 },
  { field: "last_changed", headerName: "last_changed", width: 300 },
];

interface Observation {
  id: number | string | null;
  resource: string;
  module: string;
  attribute: string | null;
  value: string | null;
  first_seen: string | null;
  last_changed: string | null;
  last_seen: string | null;
}

function fix_ids(data: Observation[]) {
  let counter = -1;
  for (const x of data) {
    if (x.id === undefined || x.id === null) {
      x.id = counter--;
    }
  }
}

async function fetch_table_data() {
  const response = await fetch("/api/observations");
  const observations: Observation[] = await response.json();
  console.log(observations);
  fix_ids(observations);
  return observations;
}

function ObservationsView() {
  const [rows, setRows] = useState(default_rows);
  // setRows(fetch_table_data());
  useEffect(() => {
    fetch_table_data().then((data) => setRows(data));
  }, []);
  return (
    <>
      <h1>Observations</h1>
      <div style={{ height: "70vh", width: "100%" }}>
        <DataGrid rows={rows} columns={columns} autoPageSize />
      </div>
    </>
  );
}

export default ObservationsView;
