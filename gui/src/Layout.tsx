import * as React from 'react';
import { Box, Tab, Tabs } from "@mui/material";
import { Outlet, useLocation, useNavigate, useParams } from "react-router-dom";

function a11yProps(index: number) {
  return {
    id: `simple-tab-${index}`,
    'aria-controls': `simple-tabpanel-${index}`,
  };
}

const tabs = ["resources", "observations", "other"];

function choose_index(value: string): number {
  for (let i = 0; i < tabs.length; i++){
    const word = tabs[i];
    if (value.includes(word)) {
      return i;
    }
  }
  return 0; // Default to resources
}

function choose_string(index: number): string {
  if (index >= tabs.length) {
    return tabs[0];
  }
  return tabs[index];
}

const Layout = () => {
  const navigate = useNavigate();
  const loc = useLocation();
  const { id } = useParams();
  const index = choose_index(loc.pathname);
  const [value, setValue] = React.useState(index);
  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    console.log(event);
      setValue(newValue);
      navigate(choose_string(newValue));
    };
  return (
    <>
      {id}
      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={value} onChange={handleChange} aria-label="basic tabs example">
            <Tab label="Resources" {...a11yProps(0)} />
            <Tab label="Observations" {...a11yProps(1)} />
            <Tab label="Other" {...a11yProps(2)} />
          </Tabs>
        </Box>
      </Box>
      <Outlet />
    </>
  )
};

export default Layout;
