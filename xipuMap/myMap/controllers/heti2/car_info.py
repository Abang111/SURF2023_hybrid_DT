from PIL import Image, ImageDraw, ImageFont
sensorsNames = [
    "front",
    "rear",
   ]
sensors = {}

#车速信息
def draw_speed(main_img, speed, x_offset, y_offset):

    size = 15

    # Create a fully transparent circle as base
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    speed_draw = ImageDraw.Draw(img)



    #Draw a smaller white circle inside
    border_thickness = int(size * 0.1)
    left_up_point = (border_thickness, border_thickness)
    right_down_point = (size - border_thickness, size - border_thickness)
    speed_draw.ellipse([left_up_point, right_down_point], fill='white')  # Note the change from outline to fill

    # Draw the speed limit number
    font_size = size // 3 + 3
    font = ImageFont.truetype("arial.ttf", font_size)
    text_width, text_height = speed_draw.textsize(str(speed), font=font)
    text_position = ((size - text_width) / 2, (size - text_height) / 2)
    speed_draw.text(text_position, str(speed), font=font, fill='black')

    # Rotate the image
    angle = 5
    img = img.rotate(-angle, resample=Image.BICUBIC, expand=False)

    # Paste the speed limit sign onto the main HUD
    position = (x_offset, y_offset)
    main_img.paste(img, position, img)

#车距信息
def draw_distance(main_img, distance):

    x_offset = 85
    y_offset = 205
    size = 15

    # Create a fully transparent circle as base
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    speed_draw = ImageDraw.Draw(img)



    #Draw a smaller white circle inside
    #border_thickness = int(size * 0.1)
    #left_up_point = (border_thickness, border_thickness)
    #right_down_point = (size - border_thickness, size - border_thickness)
    #speed_draw.ellipse([left_up_point, right_down_point], fill='white')  # Note the change from outline to fill

    # Draw the speed limit number
    font_size = size // 3 + 3
    font = ImageFont.truetype("arial.ttf", font_size)
    text_width, text_height = speed_draw.textsize(str(distance), font=font)
    text_position = ((size - text_width) / 2, (size - text_height) / 2)
    speed_draw.text(text_position, str(distance), font=font, fill='white')

    # Rotate the image
    angle = 5
    img = img.rotate(-angle, resample=Image.BICUBIC, expand=False)

    # Paste the speed limit sign onto the main HUD
    position = (x_offset, y_offset)
    main_img.paste(img, position, img)