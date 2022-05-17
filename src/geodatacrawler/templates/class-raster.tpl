         CLASS
            NAME "0 - Low"
            EXPRESSION ( [pixel] >= 0 AND [pixel] <= 10 )
            STYLE
                COLOR 244 240 240
            END # STYLE
        END #CLASS

         CLASS
            NAME "0 - 10 - Low"
            EXPRESSION ( [pixel] > 10 AND [pixel] <= 25 )
            STYLE
                COLOR 244 240 240
            END # STYLE
        END #CLASS

         CLASS
            NAME "10 - 25 - Medium"
            EXPRESSION ( [pixel] > 25 AND [pixel] <= 43 )
            STYLE
                COLOR 233 225 225
            END # STYLE
        END #CLASS

         CLASS
            NAME "25 - 43 - High"
            EXPRESSION ( [pixel] > 43 AND [pixel] <= 51 )
            STYLE
                COLOR 221 211 210
            END # STYLE
        END #CLASS

         CLASS
            NAME "43 - 51 - High"
            EXPRESSION ( [pixel] > 51 AND [pixel] <= 59 )
            STYLE
                COLOR 210 197 196
            END # STYLE
        END #CLASS

         CLASS
            NAME "51 - 59 - High"
            EXPRESSION ( [pixel] > 59 AND [pixel] <= 69 )
            STYLE
                COLOR 199 184 182
            END # STYLE
        END #CLASS

         CLASS
            NAME "59 - 69 - High"
            EXPRESSION ( [pixel] > 69 AND [pixel] <= 81 )
            STYLE
                COLOR 187 172 168
            END # STYLE
        END #CLASS

         CLASS
            NAME "69 - 81 - High"
            EXPRESSION ( [pixel] > 81 AND [pixel] <= 97 )
            STYLE
                COLOR 176 159 155
            END # STYLE
        END #CLASS

         CLASS
            NAME "81 - 97 - High"
            EXPRESSION ( [pixel] > 97 AND [pixel] <= 125 )
            STYLE
                COLOR 164 148 142
            END # STYLE
        END #CLASS

         CLASS
            NAME "> 125 - High"
            EXPRESSION ( [pixel] >= 125 )
            STYLE
                COLOR 153 136 130
            END # STYLE
        END #CLASS

