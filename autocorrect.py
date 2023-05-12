from difflib import get_close_matches
import interactions
import requests
from json import loads as to_json

countries_list = ['Aruba', 'Afghanistan', 'Angola', 'Anguilla', 'Aland Islands', 'Albania', 'Andorra', 'United Arab Emirates', 'Argentina', 'Armenia', 'American Samoa', 'Antarctica', 'French Southern Territories', 'Antigua and Barbuda', 'Australia', 'Austria', 'Azerbaijan', 'Burundi', 'Belgium', 'Benin', 'Bonaire, Sint Eustatius and Saba', 'Burkina Faso', 'Bangladesh', 'Bulgaria', 'Bahrain', 'Bahamas', 'Bosnia and Herzegovina', 'Saint Barthélemy', 'Belarus', 'Belize', 'Bermuda', 'Bolivia, Plurinational State of', 'Brazil', 'Barbados', 'Brunei Darussalam', 'Bhutan', 'Bouvet Island', 'Botswana', 'Central African Republic', 'Canada', 'Cocos (Keeling) Islands', 'Switzerland', 'Chile', 'China', "Côte d'Ivoire", 'Cameroon', 'Congo, The Democratic Republic of the', 'Congo', 'Cook Islands', 'Colombia', 'Comoros', 'Cabo Verde', 'Costa Rica', 'Cuba', 'Curaçao', 'Christmas Island', 'Cayman Islands', 'Cyprus', 'Czechia', 'Germany', 'Djibouti', 'Dominica', 'Denmark', 'Dominican Republic', 'Algeria', 'Ecuador', 'Egypt', 'Eritrea', 'Western Sahara', 'Spain', 'Estonia', 'Ethiopia', 'Finland', 'Fiji', 'Falkland Islands (Malvinas)', 'France', 'Faroe Islands', 'Micronesia, Federated States of', 'Gabon', 'United Kingdom', 'Georgia', 'Guernsey', 'Ghana', 'Gibraltar', 'Guinea', 'Guadeloupe', 'Gambia', 'Guinea-Bissau', 'Equatorial Guinea', 'Greece', 'Grenada', 'Greenland', 'Guatemala', 'French Guiana', 'Guam', 'Guyana', 'Hong Kong', 'Heard Island and McDonald Islands', 'Honduras', 'Croatia', 'Haiti', 'Hungary', 'Indonesia', 'Isle of Man', 'India', 'British Indian Ocean Territory', 'Ireland', 'Iran, Islamic Republic of', 'Iraq', 'Iceland', 'Israel', 'Italy', 'Jamaica', 'Jersey', 'Jordan', 'Japan', 'Kazakhstan', 'Kenya', 'Kyrgyzstan', 'Cambodia', 'Kiribati', 'Saint Kitts and Nevis', 'Korea, Republic of', 'Kuwait', "Lao People's Democratic Republic", 'Lebanon', 'Liberia', 'Libya', 'Saint Lucia', 'Liechtenstein', 'Sri Lanka', 'Lesotho', 'Lithuania', 'Luxembourg', 'Latvia', 'Macao', 'Saint Martin (French part)', 'Morocco', 'Monaco', 'Moldova, Republic of', 'Madagascar', 'Maldives', 'Mexico', 'Marshall Islands', 'North Macedonia', 'Mali', 'Malta', 'Myanmar', 'Montenegro', 'Mongolia', 'Northern Mariana Islands', 'Mozambique', 'Mauritania', 'Montserrat', 'Martinique', 'Mauritius', 'Malawi', 'Malaysia', 'Mayotte', 'Namibia', 'New Caledonia', 'Niger', 'Norfolk Island', 'Nigeria', 'Nicaragua', 'Niue', 'Netherlands', 'Norway', 'Nepal', 'Nauru', 'New Zealand', 'Oman', 'Pakistan', 'Panama', 'Pitcairn', 'Peru', 'Philippines', 'Palau', 'Papua New Guinea', 'Poland', 'Puerto Rico', "Korea, Democratic People's Republic of", 'Portugal', 'Paraguay', 'Palestine, State of', 'French Polynesia', 'Qatar', 'Réunion', 'Romania', 'Russian Federation', 'Rwanda', 'Saudi Arabia', 'Sudan', 'Senegal', 'Singapore', 'South Georgia and the South Sandwich Islands', 'Saint Helena, Ascension and Tristan da Cunha', 'Svalbard and Jan Mayen', 'Solomon Islands', 'Sierra Leone', 'El Salvador', 'San Marino', 'Somalia', 'Saint Pierre and Miquelon', 'Serbia', 'South Sudan', 'Sao Tome and Principe', 'Suriname', 'Slovakia', 'Slovenia', 'Sweden', 'Eswatini', 'Sint Maarten (Dutch part)', 'Seychelles', 'Syrian Arab Republic', 'Turks and Caicos Islands', 'Chad', 'Togo', 'Thailand', 'Tajikistan', 'Tokelau', 'Turkmenistan', 'Timor-Leste', 'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Tuvalu', 'Taiwan, Province of China', 'Tanzania, United Republic of', 'Uganda', 'Ukraine', 'United States Minor Outlying Islands', 'Uruguay', 'United States', 'Uzbekistan', 'Holy See (Vatican City State)', 'Saint Vincent and the Grenadines', 'Venezuela, Bolivarian Republic of', 'Virgin Islands, British', 'Virgin Islands, U.S.', 'Viet Nam', 'Vanuatu', 'Wallis and Futuna', 'Samoa', 'Yemen', 'South Africa', 'Zambia', 'Zimbabwe']

agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}

async def correctLevel(ctx, s: str, challenge_names: list):
    matches = get_close_matches(s.lower(), challenge_names, cutoff=0.85)

    if not matches:
        c = 0.85
        while c > 0.7:
            c -= 0.05
            matches = get_close_matches(s.lower(), challenge_names, cutoff=c)
            if not (not matches):
                break
    if len(matches) > 1:
        desc = f"<@{ctx.user.id}>, multiple matches for levels were found for `{s}`. Please select the one you meant:\n"
        i = 0
        print("hi")
        while i < len(matches):
            desc += f"**{i + 1}.** {matches[i]}\n"
            i += 1
        # ctx.message.options[0].value
        options = []
        for match in matches:
            options.append(interactions.Button(
                style=interactions.ButtonStyle.PRIMARY,
                label=match,
                custom_id=f"levelcorrect"
            ))
        embed = interactions.Embed(title=f"Level autocorrect", description=desc)

        return tuple([embed, options])
    elif len(matches) == 1:
        return matches[0]
    else:
        return None


async def correctCountry(ctx, s: str, limit):
    matches = get_close_matches(s.capitalize(), countries_list, cutoff=0.85)
    if not matches:
        matches = get_close_matches(s.capitalize(), countries_list, cutoff=0.8)

    if matches == ['Australia', 'Austria'] or ['Austria', 'Australia']:
        return matches[0] # australia or austria?
    if len(matches) > 1:
        desc = f"<@{ctx.user.id}>, multiple matches for countries were found for `{s}`. Please select the one you meant:\n"
        i = 0
        print("hi")
        while i < len(matches):
            desc += f"**{i + 1}.** {matches[i]}\n"
            i += 1
        #ctx.message.options[0].value
        options = []
        for match in matches:
            options.append(interactions.Button(
            style=interactions.ButtonStyle.PRIMARY,
            label=match,
            custom_id=f"countrycorrect"
            ))
        embed = interactions.Embed(title=f"Country autocorrect (Top {limit if limit else 10})", description=desc)

        return [embed, options]
    elif len(matches) == 1:
        return matches[0]
    else:
        return None
