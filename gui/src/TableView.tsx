import { useState, useEffect } from "react";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import type {} from "@mui/x-data-grid/themeAugmentation";
import { Box } from "@mui/material";
import { useNavigate } from "react-router-dom";

function columns(fields: string[]) {
  const c = [];
  for (const field of fields) {
    const o: GridColDef = {
      field: field,
      headerName: field,
      flex: 1, // fixes the issue :upside_down_face: grow to fill space
    };
    if (field === "module") {
      o.maxWidth = 100;
      o.flex = 0; // stick to 100, do not grow
    }
    if (["value", "old_value", "new_value"].includes(field)) {
      // Values can be huge (e.g. commit_signatures), don't let autosize
      // stretch the column, they're cut off (...) and the whole value is
      // shown when clicking the row:
      o.maxWidth = 400;
      // Show objects as JSON instead of [object Object]:
      o.valueFormatter = (value) =>
        typeof value === "object" ? JSON.stringify(value) : value;
    }
    c.push(o);
  }
  return c;
}

const autosizeOptions = {
  includeHeaders: true,
  includeOutliers: true,
  outliersFactor: 1.5,
  expand: true,
};

async function fetch_table_data(url: string) {
  const response = await fetch(url);
  const observations = await response.json();
  return observations;
}

function TableView({ fields, api }: { fields: string[]; api: string }) {
  const [status, setStatus] = useState("loading");
  const [rows, setRows] = useState([]);
  useEffect(() => {
    fetch_table_data(api).then((data) => {
      setRows(data);
      if (data.size === 0) {
        setStatus("empty");
      } else {
        setStatus("loaded");
      }
    });
  }, [api]);

  const navigate = useNavigate();

  if (status === "loading") {
    return (
      <>
        <span>Loading...</span>
      </>
    );
  }

  if (status === "empty") {
    return (
      <>
        <span>No data.</span>
      </>
    );
  }

  return (
    <Box sx={{ width: "100%" }}>
      <div style={{ height: "70vh", width: "100%" }}>
        <DataGrid
          onRowClick={(params) => {
            navigate("./" + params.id, { relative: "path" });
          }}
          disableRowSelectionOnClick={true}
          autoPageSize={true}
          autosizeOnMount={true}
          rows={rows}
          columns={columns(fields)}
          autosizeOptions={autosizeOptions}
        />
      </div>
    </Box>
  );
}

export default TableView;
