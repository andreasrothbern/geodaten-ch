const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'src/pages/ConfiguratorPage.tsx');
let content = fs.readFileSync(filePath, 'utf-8');

const insertionMarker = '// Convert API response to SelectedFacade format';
const earlyReturnMarker = '// Render address search form';

// Check if hook already exists before early return
const earlyReturnIndex = content.indexOf(earlyReturnMarker);
const hookExistsBeforeEarlyReturn = content.slice(0, earlyReturnIndex).includes('const handleSimplifyChange = useCallback');

if (hookExistsBeforeEarlyReturn) {
  console.log('Hook already in correct position - no changes needed');
  process.exit(0);
}

const hookCode = `  // Handle simplify epsilon change - refetch with new value
  // IMPORTANT: This useCallback MUST be before any conditional returns to avoid "Rendered more hooks" error!
  const handleSimplifyChange = useCallback(async (newEpsilon: number | null) => {
    setSimplifyEpsilon(newEpsilon);
    if (buildingData?.building.address) {
      setSimplifyLoading(true);
      try {
        await fetchBuildingData(buildingData.building.address, project, newEpsilon);
      } finally {
        setSimplifyLoading(false);
      }
    }
  }, [buildingData?.building.address, project, fetchBuildingData]);

  `;

const insertionIndex = content.indexOf(insertionMarker);
if (insertionIndex !== -1) {
  const newContent = content.slice(0, insertionIndex) + hookCode + content.slice(insertionIndex);
  fs.writeFileSync(filePath, newContent, 'utf-8');
  console.log('SUCCESS: Hook inserted before early return');
} else {
  console.log('ERROR: Could not find insertion point');
  process.exit(1);
}