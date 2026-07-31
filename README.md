# Tórshavn Waste

A custom Home Assistant integration for waste collection in Tórshavn Municipality.

The integration provides collection information for:

- regular household waste
- green-bin collection
- grey and red waste-bag delivery months
- tomorrow indicators
- Home Assistant calendar events

## Features

The integration creates:

- a sensor for the next regular waste collection
- a sensor for the next green-bin collection
- a binary sensor for regular waste collection tomorrow
- a binary sensor for green-bin collection tomorrow
- a calendar containing upcoming collection events

## Data sources

Regular household-waste collection data is retrieved from the public ArcGIS service provided by Tórshavn Municipality.

Green-bin collection dates are based on the annual calendar published by Kommunala Brennistøðin.

Holiday-related changes to regular weekly collection dates are not currently included. The integration does not invent or estimate moved collection dates.

## Installation with HACS

Until the integration is available in the default HACS repository list, add it as a custom repository:

1. Open HACS in Home Assistant.
2. Open the menu in the upper-right corner.
3. Select **Custom repositories**.
4. Add:

   `https://github.com/fridberg479/ha-torshavn-waste`

5. Select **Integration** as the category.
6. Download **Tórshavn Waste**.
7. Restart Home Assistant.

Then go to:

**Settings → Devices & services → Add integration**

Search for:

**Tórshavn Waste**

## Manual installation

Copy this directory:

`custom_components/torshavn_waste`

to:

`/config/custom_components/torshavn_waste`

Restart Home Assistant and add the integration from **Settings → Devices & services**.

## Configuration

Enter the street name without a house number.

If the street is listed in the green-bin calendar, the integration selects the relevant collection area. If the street belongs to more than one area, you will be asked to select the correct area.

If the street is not listed, the integration asks for the town or village. This supports settlement-wide collection areas, including:

### Area 1

- Kaldbaksbotnur
- Kaldbak
- Kollafjørður
- Langasandur
- Oyrareingir
- Hvítanes
- Signabøur

### Area 6

- Argir
- Kirkjubøur
- Norðadalur
- Syðradalur
- Velbastaður

Common inflected forms such as `Argjum`, `Kirkjubø` and `Kollafirði` are supported.

## Home Assistant location

Regular household-waste collection is found using the home coordinates configured in Home Assistant.

Check the coordinates under:

**Settings → System → General**

The coordinates should represent the address for which the integration is configured.

## Entities

The integration currently creates:

- `Next green-bin collection`
- `Next general waste collection`
- `Green-bin collection tomorrow`
- `General waste collection tomorrow`
- `Waste collection`

Entity names are available in English and Faroese.

## Limitations

- Green-bin data currently covers the 2026 calendar.
- Regular collection is calculated from the weekday returned by the municipal ArcGIS service.
- Holiday-related schedule changes are not included unless an authoritative source provides the changed date.
- The Home Assistant coordinates are used for the ArcGIS lookup. Multiple configured addresses with different coordinates are not yet supported.

## Development

Run the test suite from the repository root:

```powershell
python -m pytest -v
```

Build the green-calendar JSON data:

```powershell
python scripts/build_green_calendar.py source/green_calendar_2026.pdf
```

The generated data is written to:

- `data/green_calendar_2026.json`
- `custom_components/torshavn_waste/data/green_calendar_2026.json`

## Support

Report problems through the GitHub issue tracker.

When reporting a problem, include:

- the Home Assistant version
- the integration version
- relevant Home Assistant log messages
- the street and settlement involved, unless that information is private

## Disclaimer

This is an independent community integration. It is not an official integration from Tórshavn Municipality or Kommunala Brennistøðin.
