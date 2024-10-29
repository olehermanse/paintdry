import { useState, useEffect } from "react";
import "./ResourcesView.css";
import { DataGrid, GridRowsProp, GridColDef, GridRowParams } from "@mui/x-data-grid";
import type {} from "@mui/x-data-grid/themeAugmentation";
import { useNavigate } from "react-router-dom";

const default_rows: GridRowsProp = [
  {
    first_seen: "Thu, 24 Oct 2024 20:14:56 GMT",
    last_seen: "Thu, 24 Oct 2024 20:14:56 GMT",
    modules: ["Loading..."],
    resource: "Loading...",
    id: "Loading...",
    source: "http",
  },
];

const columns: GridColDef[] = [
  { field: "id", headerName: "id", maxWidth: 80 },
  { field: "resource", headerName: "resource" },
  { field: "modules", headerName: "modules" },
  { field: "source", headerName: "source" },
  { field: "first_seen", headerName: "first_seen" },
  { field: "last_seen", headerName: "last_seen" },
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

const autosizeOptions = {
  includeHeaders: true,
  includeOutliers: true,
  outliersFactor: 1.5,
  expand: true,
};

function ResourcesView() {
  const [rows, setRows] = useState(default_rows);
  // setRows(fetch_table_data());
  useEffect(() => {
    fetch_table_data().then((data) => setRows(data));
  }, []);

  const navigate = useNavigate();
  function rowClick(params: GridRowParams){
    console.log(params);
    navigate("/ui/resources/" + params.id);
  }
  return (
    <>
      <h1>Resources</h1>
      <div style={{ height: "70vh", width: "100%" }}>
        <DataGrid disableRowSelectionOnClick={true} onRowClick={ (params) => rowClick(params) } autoPageSize={true} autosizeOnMount={true} rows={rows} columns={columns} autosizeOptions={autosizeOptions} />
      </div>
    </>
  );
}

export default ResourcesView;
