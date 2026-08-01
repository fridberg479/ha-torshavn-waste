# Tórshavn Waste

A custom Home Assistant integration for waste collection in Tórshavn Municipality, Faroe Islands.

The integration provides information about:

- regular household-waste collection
- green-bin collection
- delivery of red and grey waste bags
- collections taking place tomorrow
- possible holiday-related schedule changes
- upcoming collection events in a Home Assistant calendar

## Features

The integration creates:

- a date sensor for the next regular household-waste collection
- a date sensor for the next green-bin collection
- a sensor for the next delivery month of red and grey waste bags
- a binary sensor for regular waste collection tomorrow
- a binary sensor for green-bin collection tomorrow
- a binary sensor warning when regular collection falls on a listed holiday
- a calendar containing upcoming regular and green-bin collection events

Additional attributes include:

- number of days until collection
- readable Faroese dates
- Faroese weekday names
- relative text such as `í dag`, `í morgin` and `um 5 dagar`
- holiday name and warning status
- delivery year and month for red and grey bags
- number of months until the next bag delivery

## Data sources

Regular household-waste collection data is retrieved from the public ArcGIS service provided by Tórshavn Municipality.

Green-bin collection dates and red/grey bag-delivery months are based on the annual calendar published by Kommunala Brennistøðin.

Holiday warnings are based on the holiday data included with the integration.

## Holiday warnings

Regular household-waste collection is normally calculated from the weekday returned by the municipal ArcGIS service.

When the calculated collection date falls on a listed holiday, the integration:

- keeps showing the regular collection date
- marks the date as a holiday
- provides the holiday name
- activates the holiday-warning binary sensor
- adds a warning to the calendar event

The integration does **not** automatically move the collection date.

A holiday warning means that the normal schedule may have changed. It does not confirm the actual replacement date.

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

Restart Home Assistant and add the integration from:

**Settings → Devices & services → Add integration**

## Configuration

Enter the street name without a house number.

If the street is listed in the green-bin calendar, the integration selects the relevant collection area.

If the street belongs to more than one area, you will be asked to select the correct area.

If the street is not listed, the integration asks for the town or village. This supports settlement-wide collection areas, including the following.

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

The street and settlement entered during setup are currently used for the green-bin calendar. The ArcGIS lookup for regular waste uses the global Home Assistant coordinates.

## Entities

The integration currently creates the following entities.

### Sensors

- `Next green-bin collection`
- `Next general waste collection`
- `Next red and grey bag delivery`

### Binary sensors

- `Green-bin collection tomorrow`
- `General waste collection tomorrow`
- `General waste collection may be changed`

### Calendar

- `Waste collection`

Entity names are available in English and Faroese.

Actual entity IDs depend on the name of the configured address.

## Sensor attributes

### Next green-bin collection

Important attributes include:

- `days_until`
- `formatted_date`
- `weekday_name_fo`
- `relative_text`
- `area`
- `calendar_year`
- `upcoming_collections`
- `red_bag_months`
- `grey_bag_months`

### Next general waste collection

Important attributes include:

- `days_until`
- `formatted_date`
- `weekday_name_fo`
- `relative_text`
- `weekday_name`
- `route_id`
- `is_holiday`
- `holiday_name`
- `schedule_may_be_changed`

### Next red and grey bag delivery

The state is shown as `YYYY-MM`, because the source calendar specifies a month but not an exact delivery date.

Important attributes include:

- `formatted_month`
- `delivery_year`
- `delivery_month`
- `months_until`
- `bag_types`

## Example dashboard card

Replace the example entity IDs with the IDs created for your address.

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      ## 🗑️ Ruskinnsavning
      **Your address**

  - type: grid
    columns: 2
    square: false
    cards:
      - type: tile
        entity: sensor.your_address_next_general_waste_collection
        name: Vanligt rusk
        icon: mdi:trash-can
        color: blue
        vertical: true
        state_content:
          - formatted_date

      - type: tile
        entity: sensor.your_address_next_green_bin_collection
        name: Grøna ílatið
        icon: mdi:recycle
        color: green
        vertical: true
        state_content:
          - formatted_date

  - type: tile
    entity: sensor.your_address_next_red_and_grey_bag_delivery
    name: Næsta útbering av reyðum og gráum posum
    icon: mdi:bag-personal
    color: grey
    state_content:
      - formatted_month

  - type: conditional
    conditions:
      - condition: state
        entity: binary_sensor.your_address_general_waste_collection_tomorrow
        state: "on"
    card:
      type: tile
      entity: binary_sensor.your_address_general_waste_collection_tomorrow
      name: Minst til vanliga ruskið í kvøld
      icon: mdi:trash-can-clock
      color: orange

  - type: conditional
    conditions:
      - condition: state
        entity: binary_sensor.your_address_green_bin_collection_tomorrow
        state: "on"
    card:
      type: tile
      entity: binary_sensor.your_address_green_bin_collection_tomorrow
      name: Minst til grøna ílatið í kvøld
      icon: mdi:recycle-variant
      color: green

  - type: conditional
    conditions:
      - condition: state
        entity: binary_sensor.your_address_general_waste_collection_may_be_changed
        state: "on"
    card:
      type: tile
      entity: binary_sensor.your_address_general_waste_collection_may_be_changed
      name: Innsavningin kann vera broytt
      icon: mdi:calendar-alert
      color: red
      state_content:
        - holiday_name
        - collection_date
```

The conditional cards are hidden during normal dashboard use while their binary sensors are `off`. Home Assistant may still show them while the dashboard is being edited.

## Limitations

- Green-bin data currently covers the 2026 calendar.
- Red and grey bag-delivery information currently covers the months listed in the 2026 calendar.
- Bag-delivery data specifies only a month, not an exact date.
- Regular collection is calculated from the weekday returned by the municipal ArcGIS service.
- A holiday warning does not identify or calculate the replacement collection date.
- Public announcements about changed collection dates are not automatically interpreted.
- The Home Assistant coordinates are used for the ArcGIS lookup.
- Multiple configured addresses with different ArcGIS coordinates are not currently supported.

## Updating calendar data

The integration includes the green-bin calendar as versioned data.

A new calendar year should not be added until an authoritative calendar has been published.

Do not estimate future green-bin collection dates from the previous year.

## Development

Run the complete test suite from the repository root:

```powershell
python -m pytest
```

Run the test suite with verbose output:

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
- the entity showing the problem
- the street and settlement involved, unless that information is private

## Disclaimer

This is an independent community integration.

It is not an official integration from Tórshavn Municipality or Kommunala Brennistøðin. Collection schedules may change. Always follow authoritative information from the relevant public authorities.